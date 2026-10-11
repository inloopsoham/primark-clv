"""
models.py - Stage 3: predict churn risk and Customer Lifetime Value (CLV).

THE IDEA IN PLAIN ENGLISH
  CLV (next 6 / 12 months) = expected number of visits  x  expected spend per visit

  1. Expected visits come from a BG/NBD model (a classic "survival" style model).
     For every customer it asks two things:
       - Is this customer still active, or have they quietly left?   -> churn risk
       - If active, how many more visits should we expect?
     It uses only three numbers per customer: how many repeat visits, when the
     last one was, and how long they have been a customer.
     (We use a small variant that lets a customer leave right after their first
     visit, because that is common in retail.)

  2. Spend per visit comes from a gradient boosting model (LightGBM). It learns
     from basket size, category mix, returns, loyalty, email behaviour, age...

  3. Final CLV = the average of two views: (BG/NBD visits x GBM spend per visit)
     and a GBM that predicts spend directly while also seeing the BG/NBD signals.

  4. We compare everything against a simple baseline ("they will keep spending
     what they spent before") on a year the models never saw.

HOW WE TEST IT HONESTLY
  Train on customers as of 30 Sep 2024 -> check predictions against what they
  really did in Oct 2024 - Sep 2025... then the same for the held-out year
  (features as of 30 Sep 2025, results Oct 2025 - Sep 2026). Only the
  held-out year is used for the scorecard.

Run from the project root:   python -m src.models
"""
import json
import pickle
import time

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln, hyp2f1
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from src import config as C
from src.features import HORIZON_DAYS

try:                                   # LightGBM is the preferred engine ...
    import lightgbm as lgb
    GBM_ENGINE = "LightGBM"
except Exception:                      # ... scikit-learn is the safety net
    lgb = None
    GBM_ENGINE = "scikit-learn HistGradientBoosting"
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

HORIZONS = ("6m", "12m")
WEEKS = {h: HORIZON_DAYS[h] / 7.0 for h in HORIZONS}
MODEL_DIR = C.OUTPUT_DIR / "models"
A_MIN = 1.01                           # keeps the BG/NBD maths well-behaved
FINAL_MODEL = "blend"                  # final CLV = average of the hybrid and stacked models

CAT_LEVELS = {
    "gender": ["F", "M", "X"],
    "region": list(C.REGION_WEIGHTS),
    "country": sorted({s[3] for s in C.STORES}),
    "top_category": C.CATEGORIES,
}
NOT_FEATURES = {"customer_id", "snapshot_date", "first_order", "last_order"}


# ============================================================================
# PART 1 - BG/NBD (churn and expected visits)
# ============================================================================
def _unpack(p):
    """Optimiser works with log-numbers so parameters stay positive."""
    r, alpha, b = np.exp(p[0]), np.exp(p[1]), np.exp(p[3])
    a = A_MIN + np.exp(p[2])
    return r, alpha, a, b


def _nll(p, x, tx, T):
    """Negative log-likelihood (smaller = the model explains the data better)."""
    r, al, a, b = _unpack(p)
    t_alive = gammaln(b + x + 1) - (r + x) * np.log(al + T)             # still active at T
    t_gone = np.log(a) + gammaln(b + x) - (r + x) * np.log(al + tx)     # left after last visit
    ll = (gammaln(r + x) - gammaln(r) + r * np.log(al)
          + gammaln(a + b) - gammaln(b) - gammaln(a + b + x + 1)
          + np.logaddexp(t_alive, t_gone))
    return -ll.mean()


def bgnbd_inputs(df):
    return (df["bgnbd_frequency"].to_numpy(float),
            df["bgnbd_recency_weeks"].to_numpy(float),
            df["bgnbd_T_weeks"].to_numpy(float))


def fit_bgnbd(df):
    """Learn the 4 BG/NBD numbers from a snapshot table."""
    x, tx, T = bgnbd_inputs(df)
    best = None
    for start in ([0.0, 2.3, -0.7, 1.6], [0.3, 2.5, 0.0, 2.0], [-0.3, 2.0, -1.0, 1.0]):
        res = minimize(_nll, np.array(start), args=(x, tx, T), method="L-BFGS-B",
                       bounds=[(-4, 5)] * 4)
        if best is None or res.fun < best.fun:
            best = res
    r, alpha, a, b = _unpack(best.x)
    return {"r": float(r), "alpha": float(alpha), "a": float(a), "b": float(b),
            "n_customers": int(len(df)), "neg_log_likelihood": float(best.fun)}


def p_alive(params, x, tx, T):
    """Probability the customer is still active at the snapshot date."""
    r, al, a, b = params["r"], params["alpha"], params["a"], params["b"]
    log_ratio = np.log(a) - np.log(b + x) + (r + x) * (np.log(al + T) - np.log(al + tx))
    return 1.0 / (1.0 + np.exp(np.minimum(log_ratio, 700)))


def visits_if_active(params, weeks, x, T):
    """Expected visits in the next `weeks` IF the customer is still active."""
    r, al, a, b = params["r"], params["alpha"], params["a"], params["b"]
    beta = b + x + 1
    z = weeks / (al + T + weeks)
    h = hyp2f1(r + x, beta, a + beta - 1, z)
    core = (a + beta - 1) / (a - 1) * (1 - ((al + T) / (al + T + weeks)) ** (r + x) * h)
    return np.clip(np.nan_to_num(core, nan=0.0, posinf=0.0), 0, None)


def add_bgnbd(df, params):
    """Add churn / visit columns to a snapshot table."""
    df = df.copy()
    x, tx, T = bgnbd_inputs(df)
    pa = p_alive(params, x, tx, T)
    df["p_alive"] = pa
    df["churn_risk"] = 1 - pa
    for h in HORIZONS:
        core = visits_if_active(params, WEEKS[h], x, T)
        df[f"visits_if_active_{h}"] = core
        df[f"exp_visits_{h}"] = pa * core
    return df


# ============================================================================
# PART 2 - Gradient boosting (spend per visit, and a direct spend model)
# ============================================================================
def feature_columns(df):
    return [c for c in df.columns
            if c not in NOT_FEATURES and not c.startswith("target_")
            and c not in ("p_alive", "churn_risk")
            and not c.startswith("exp_visits_") and not c.startswith("visits_if_active_")
            and not c.startswith("pred_") and not c.startswith("clv_")
            and not c.startswith("hist_") and not c.startswith("baseline_")]


def make_X(df, cols):
    X = df[cols].copy()
    for c, levels in CAT_LEVELS.items():
        if c in X.columns:
            X[c] = pd.Categorical(X[c], categories=levels)
    return X


def new_gbm(kind):
    """kind = 'spend' (many zeros, never negative) or 'aov' (average basket)."""
    if lgb is not None:
        return lgb.LGBMRegressor(
            objective="tweedie" if kind == "spend" else "regression",
            n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=50,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=2.0,
            random_state=C.SEED, verbose=-1)
    return HistGradientBoostingRegressor(
        loss="poisson" if kind == "spend" else "squared_error",
        max_iter=300, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=50,
        l2_regularization=2.0, categorical_features="from_dtype", random_state=C.SEED)


def fit_gbms(train):
    """Train the spend-per-visit model and one direct spend model per horizon."""
    cols = feature_columns(train)
    stack_cols = cols + ["p_alive"] + [f"exp_visits_{h}" for h in HORIZONS]

    # (a) spend per visit: only customers who actually came back, weighted by visits
    seen = train[train["target_visits_12m"] > 0]
    aov_model = new_gbm("aov")
    aov_model.fit(make_X(seen, cols), seen["target_aov_12m"], sample_weight=seen["target_visits_12m"])

    # (b) direct spend models that also see the BG/NBD signals ("stacked")
    direct = {}
    for h in HORIZONS:
        m = new_gbm("spend")
        m.fit(make_X(train, stack_cols), train[f"target_spend_{h}"])
        direct[h] = m
    return {"cols": cols, "stack_cols": stack_cols, "aov": aov_model, "direct": direct}


def predict_all(df, gbms):
    """All model families for one snapshot table (which already has BG/NBD columns)."""
    out = df[["customer_id"]].copy()
    for c in ("p_alive", "churn_risk", "exp_visits_6m", "exp_visits_12m",
              "visits_if_active_6m", "visits_if_active_12m"):
        out[c] = df[c].to_numpy()

    net_keep = 1 - df["refund_ratio"].to_numpy()
    out["hist_net_aov"] = df["aov"].to_numpy() * net_keep
    out["pred_aov"] = np.clip(gbms["aov"].predict(make_X(df, gbms["cols"])), 1.0, None)

    for h in HORIZONS:
        days = HORIZON_DAYS[h]
        # 1) baseline: keep spending at the historical run-rate
        out[f"baseline_{h}"] = (df["total_spend"].to_numpy() * net_keep
                                / np.maximum(df["tenure_days"].to_numpy(), 90) * days)
        # 2) BG/NBD visits x historical basket
        out[f"clv_bgnbd_{h}"] = out[f"exp_visits_{h}"] * out["hist_net_aov"]
        # 3) hybrid: BG/NBD visits x GBM basket
        out[f"clv_hybrid_{h}"] = out[f"exp_visits_{h}"] * out["pred_aov"]
        # 4) stacked: GBM spend model that also sees churn / visit signals
        out[f"clv_stacked_{h}"] = np.clip(
            gbms["direct"][h].predict(make_X(df, gbms["stack_cols"])), 0, None)
        # 5) final: average of 3 and 4 (two different views, steadier than either alone)
        out[f"clv_blend_{h}"] = (out[f"clv_hybrid_{h}"] + out[f"clv_stacked_{h}"]) / 2
    return out


def importance_table(model, X, y, top=15):
    """Which inputs matter most (share of total, sums to 100%)."""
    if lgb is not None and hasattr(model, "booster_"):
        imp = model.booster_.feature_importance(importance_type="gain").astype(float)
    else:
        idx = np.random.default_rng(C.SEED).choice(len(X), min(3000, len(X)), replace=False)
        pi = permutation_importance(model, X.iloc[idx], y.iloc[idx], n_repeats=3,
                                    random_state=C.SEED, scoring="neg_mean_absolute_error")
        imp = np.clip(pi.importances_mean, 0, None)
    imp = imp / max(imp.sum(), 1e-12)
    t = pd.DataFrame({"feature": X.columns, "importance": imp})
    return t.sort_values("importance", ascending=False).head(top).round(4).to_dict("records")


# ============================================================================
# PART 3 - Scorecard
# ============================================================================
def score_one(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    n10 = max(1, int(len(y) * 0.10))
    top = y[np.argsort(-p)[:n10]].sum() / y.sum()
    best = np.sort(y)[::-1][:n10].sum() / y.sum()
    return {
        "mae_gbp": round(float(np.abs(y - p).mean()), 2),
        "rmse_gbp": round(float(np.sqrt(((y - p) ** 2).mean())), 2),
        "r2": round(float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()), 3),
        "rank_correlation": round(float(spearmanr(y, p)[0]), 3),
        "total_bias_pct": round(float(p.sum() / y.sum() - 1) * 100, 1),
        "top10pct_captures_pct": round(float(top) * 100, 1),
        "perfect_top10pct_captures_pct": round(float(best) * 100, 1),
    }


MODEL_NAMES = {
    "baseline": "Baseline: historical run-rate",
    "bgnbd": "BG/NBD visits x historical basket",
    "hybrid": "Hybrid: BG/NBD visits x GBM basket",
    "stacked": "Stacked: GBM + BG/NBD signals",
    "blend": "Final: blend of hybrid + stacked",
}


def build_scorecard(test_df, pred):
    rows = []
    for h in HORIZONS:
        y = test_df[f"target_spend_{h}"].to_numpy()
        for key, col in (("baseline", f"baseline_{h}"), ("bgnbd", f"clv_bgnbd_{h}"),
                         ("hybrid", f"clv_hybrid_{h}"), ("stacked", f"clv_stacked_{h}"),
                         ("blend", f"clv_blend_{h}")):
            rows.append({"horizon": h, "model_key": key, "model": MODEL_NAMES[key],
                         **score_one(y, pred[col])})
    return rows


def decile_table(y, p, n=10):
    d = pd.DataFrame({"y": y, "p": p})
    d["decile"] = pd.qcut(d["p"].rank(method="first", ascending=False), n, labels=range(1, n + 1))
    t = d.groupby("decile", observed=True).agg(customers=("y", "size"),
                                                predicted_avg=("p", "mean"),
                                                actual_avg=("y", "mean")).round(2)
    return t.reset_index().astype({"decile": int}).to_dict("records")


def visits_calibration(test_df):
    """Predicted vs actual 12-month visits, grouped by past repeat visits."""
    d = pd.DataFrame({"x": test_df["bgnbd_frequency"].clip(upper=8),
                      "pred": test_df["exp_visits_12m"], "actual": test_df["target_visits_12m"]})
    t = d.groupby("x").agg(customers=("x", "size"), predicted=("pred", "mean"),
                           actual=("actual", "mean")).round(3).reset_index()
    t["repeat_visits"] = t["x"].map(lambda v: f"{int(v)}+" if v >= 8 else str(int(v)))
    return t.drop(columns="x").to_dict("records")


# ============================================================================
# Main
# ============================================================================
def run():
    t0 = time.time()
    C.OUTPUT_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    train = pd.read_parquet(C.OUTPUT_DIR / "features_train.parquet")
    test = pd.read_parquet(C.OUTPUT_DIR / "features_test.parquet")
    score = pd.read_parquet(C.OUTPUT_DIR / "features_score.parquet")
    print(f"GBM engine: {GBM_ENGINE}")

    # ---- A. Honest test: learn on the train snapshot, grade on the held-out year
    print("1/4 Fitting BG/NBD on the training snapshot ...")
    p_eval = fit_bgnbd(train)
    train_b, test_b = add_bgnbd(train, p_eval), add_bgnbd(test, p_eval)
    print("2/4 Training gradient boosting models ...")
    gbms_eval = fit_gbms(train_b)
    test_pred = predict_all(test_b, gbms_eval)
    scorecard = build_scorecard(test_b, test_pred)

    final_col = lambda h: f"clv_{FINAL_MODEL}_{h}"
    auc_model = roc_auc_score(test_b["target_visits_12m"] == 0, test_b["churn_risk"])
    auc_recency = roc_auc_score(test_b["target_visits_12m"] == 0, test_b["recency_days"])

    # ---- B. Final models: use all history to score "today"
    print("3/4 Refitting on all history and scoring today's customers ...")
    p_final = fit_bgnbd(score)
    pooled = pd.concat([train_b, test_b], ignore_index=True)
    gbms_final = fit_gbms(pooled)
    score_b = add_bgnbd(score, p_final)
    sp = predict_all(score_b, gbms_final)
    for h in HORIZONS:
        sp[f"clv_{h}"] = sp[final_col(h)]
        sp[f"potential_clv_{h}"] = np.where(sp["p_alive"] > 0.02, sp[f"clv_{h}"] / sp["p_alive"], np.nan)
    # "Potential" = what the customer would be worth if kept active. Where the
    # model is nearly sure they have left, fall back to the hybrid estimate.
    for h in HORIZONS:
        fallback = sp[f"visits_if_active_{h}"] * sp["pred_aov"]
        pot = np.minimum(sp[f"potential_clv_{h}"].fillna(fallback), np.maximum(fallback * 1.5, 1))
        sp[f"potential_clv_{h}"] = np.maximum(pot, sp[f"clv_{h}"])
        sp[f"revenue_at_risk_{h}"] = sp[f"potential_clv_{h}"] * sp["churn_risk"]

    # ---- C. Extra credibility checks
    truth = pd.read_csv(C.DATA_DIR / "_ground_truth_for_validation.csv")
    chk = sp.merge(truth, on="customer_id")
    auc_truth = roc_auc_score(chk["left_in_window"], chk["churn_risk"])
    mean_by_truth = chk.groupby("left_in_window")["churn_risk"].mean().round(3).to_dict()

    # ---- D. Save everything
    print("4/4 Saving predictions, metrics and models ...")
    sp.to_parquet(C.OUTPUT_DIR / "predictions_score.parquet", index=False)
    tp = test_pred.copy()
    for h in HORIZONS:
        tp[f"clv_{h}"] = tp[final_col(h)]
        tp[f"actual_spend_{h}"] = test_b[f"target_spend_{h}"].to_numpy()
    tp["actual_visits_12m"] = test_b["target_visits_12m"].to_numpy()
    tp.to_parquet(C.OUTPUT_DIR / "predictions_test.parquet", index=False)

    cols, scols = gbms_eval["cols"], gbms_eval["stack_cols"]
    metrics = {
        "gbm_engine": GBM_ENGINE,
        "final_model": FINAL_MODEL,
        "final_model_name": MODEL_NAMES[FINAL_MODEL],
        "snapshots": {"train": "2024-09-30", "test": "2025-09-30", "score": "2026-09-30"},
        "scorecard": scorecard,
        "churn": {"auc_bgnbd": round(auc_model, 3), "auc_recency_only": round(auc_recency, 3),
                  "auc_vs_hidden_truth": round(auc_truth, 3),
                  "avg_churn_risk_if_truly_left": mean_by_truth.get(1),
                  "avg_churn_risk_if_truly_active": mean_by_truth.get(0)},
        "bgnbd_params_train": p_eval,
        "bgnbd_params_final": p_final,
        "bgnbd_true_values_in_generator": {"r": C.LAM_SHAPE, "alpha": round(1 / C.LAM_SCALE, 2),
                                           "a": C.DROP_A, "b": C.DROP_B},
        "calibration_deciles_12m": decile_table(test_b["target_spend_12m"].to_numpy(),
                                                test_pred[final_col("12m")].to_numpy()),
        "visits_calibration_12m": visits_calibration(test_b),
        "importance_basket_model": importance_table(
            gbms_eval["aov"], make_X(test_b[test_b["target_visits_12m"] > 0], cols),
            test_b.loc[test_b["target_visits_12m"] > 0, "target_aov_12m"]),
        "importance_stacked_model_12m": importance_table(
            gbms_eval["direct"]["12m"], make_X(test_b, scols), test_b["target_spend_12m"]),
        "today_totals": {h: {"clv_gbp": round(float(sp[f"clv_{h}"].sum()), 0),
                             "revenue_at_risk_gbp": round(float(sp[f"revenue_at_risk_{h}"].sum()), 0),
                             "baseline_gbp": round(float(sp[f"baseline_{h}"].sum()), 0)}
                         for h in HORIZONS},
    }
    (C.OUTPUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2, default=float))
    (MODEL_DIR / "bgnbd_params.json").write_text(json.dumps(p_final, indent=2))
    with open(MODEL_DIR / "gbm_models.pkl", "wb") as f:
        pickle.dump(gbms_final, f)

    print_summary(metrics, sp, time.time() - t0)
    return metrics


def print_summary(m, sp, secs):
    print("\n" + "=" * 78)
    print("MODEL SCORECARD  (held-out year, customers the models never learned from)")
    print("=" * 78)
    for h in HORIZONS:
        print(f"\n  Next {h.replace('m', ' months')}: how close is each prediction to what customers really spent?")
        print(f"  {'model':<40}{'MAE':>7}{'R2':>8}{'rank':>7}{'bias%':>8}{'top10%':>9}")
        for r in [r for r in m["scorecard"] if r["horizon"] == h]:
            mark = " <- final" if r["model_key"] == m["final_model"] else ""
            print(f"  {r['model']:<40}{r['mae_gbp']:>7.2f}{r['r2']:>8.3f}"
                  f"{r['rank_correlation']:>7.2f}{r['total_bias_pct']:>8.1f}"
                  f"{r['top10pct_captures_pct']:>8.1f}%{mark}")
        perfect = [r for r in m["scorecard"] if r["horizon"] == h][0]["perfect_top10pct_captures_pct"]
        print(f"  (top10% = share of all real spend held by the 10% we ranked highest; perfect = {perfect}%)")
    c = m["churn"]
    print("\n" + "-" * 78)
    print("CHURN: does the model spot customers who will not come back?")
    print(f"  AUC, BG/NBD churn risk          {c['auc_bgnbd']}   (0.5 = coin flip, 1.0 = perfect)")
    print(f"  AUC, 'days since last visit'    {c['auc_recency_only']}   (simple rule of thumb)")
    print(f"  AUC vs hidden answer key        {c['auc_vs_hidden_truth']}")
    print(f"  Avg churn risk: customers who truly left {c['avg_churn_risk_if_truly_left']}  "
          f"vs still active {c['avg_churn_risk_if_truly_active']}")
    t, g = m["bgnbd_params_train"], m["bgnbd_true_values_in_generator"]
    print("\n" + "-" * 78)
    print("Did BG/NBD rediscover the hidden behaviour we built into the data?")
    print(f"  {'':<10}{'learned':>10}{'true':>10}")
    for k in ("r", "alpha", "a", "b"):
        print(f"  {k:<10}{t[k]:>10.2f}{g[k]:>10.2f}")
    print("\n" + "-" * 78)
    print("TODAY (30 Sep 2026): totals across all 20,000 customers")
    for h in HORIZONS:
        d = m["today_totals"][h]
        print(f"  {h:>3}: predicted CLV GBP {d['clv_gbp']:>10,.0f}   revenue at risk GBP "
              f"{d['revenue_at_risk_gbp']:>10,.0f}   (baseline would say GBP {d['baseline_gbp']:,.0f})")
    demo = sp[sp["customer_id"] == f"C{C.DEMO_CUSTOMER_INDEX + 1:05d}"].iloc[0]
    print("\n" + "-" * 78)
    print(f"DEMO CUSTOMER {demo['customer_id']}")
    print(f"  still active?        {demo['p_alive']:.0%}   -> churn risk {demo['churn_risk']:.0%}")
    print(f"  CLV 6m / 12m         GBP {demo['clv_6m']:.0f} / GBP {demo['clv_12m']:.0f}")
    print(f"  worth if kept active GBP {demo['potential_clv_12m']:.0f} over 12 months   "
          f"revenue at risk GBP {demo['revenue_at_risk_12m']:.0f}")
    print(f"  baseline would say   GBP {demo['baseline_12m']:.0f} over 12 months")
    print("=" * 78)
    print(f"Done in {secs:.0f} seconds. Files in: {C.OUTPUT_DIR}")


if __name__ == "__main__":
    run()
