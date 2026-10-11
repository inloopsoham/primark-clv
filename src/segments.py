"""
segments.py - Stage 4: turn predictions into ACTIONS.

Two questions decide which of four groups a customer falls into:

  1. How valuable would they be if we keep them active?   (potential 12m CLV)
  2. How likely are they to drift away?                   (churn risk)

                          low churn risk        high churn risk
      high value          GROW                  PROTECT   <- most urgent
      lower value         MAINTAIN              WIN BACK

For every customer we also write plain-English "why flagged" reasons and a
suggested next action, and for every segment we estimate what a campaign could
recover. Campaign numbers are ILLUSTRATIVE ASSUMPTIONS (see CAMPAIGNS below):
they are meant to be adjusted with Primark's own response and cost data.

Run from the project root:   python -m src.segments
"""
import json

import numpy as np
import pandas as pd

from src import config as C

# ----------------------------------------------------------------------------
# Rules (change here, everything downstream follows)
# ----------------------------------------------------------------------------
HIGH_VALUE_TOP_SHARE = 0.30     # top 30 % by potential 12m CLV count as "high value"
HIGH_RISK_CUTOFF = 0.50         # churn risk at or above this is "high risk"

SEGMENT_ORDER = ["Protect", "Grow", "Win back", "Maintain"]

# Campaign assumptions per segment (ILLUSTRATIVE - to be replaced with real data)
#   save_rate     share of revenue-at-risk a campaign wins back / protects
#   upside_rate   (Grow only) extra spend from upsell, as share of current CLV
#   cost_contact  cost to contact one customer (GBP): email / push / SMS / admin
#   offer_cost    share of recovered revenue given away as discount, offer or reward
CAMPAIGNS = {
    "Protect": dict(
        goal="Stop high-value customers drifting away",
        play="Personal outreach before they lapse: app push and email with member-only early access "
             "and an offer in their favourite category",
        channel="App push + email",
        kpi="Visit within 30 days",
        save_rate=0.20, upside_rate=0.0, cost_contact=0.40, offer_cost=0.15),
    "Grow": dict(
        goal="Deepen loyalty of healthy high-value customers",
        play="Loyalty tier upgrade, cross-category bundles and first access to new ranges. "
             "Reward, don't discount",
        channel="App + loyalty communications",
        kpi="Spend per customer",
        save_rate=0.0, upside_rate=0.05, cost_contact=0.25, offer_cost=0.30),
    "Win back": dict(
        goal="Reactivate lapsing lower-value customers cheaply",
        play="Low-cost reactivation: single email or SMS with a modest offer on their top category",
        channel="Email + SMS",
        kpi="Reactivation rate",
        save_rate=0.12, upside_rate=0.0, cost_contact=0.10, offer_cost=0.20),
    "Maintain": dict(
        goal="Keep steady customers engaged at minimal cost",
        play="Automated seasonal nurture (back-to-school, Christmas). No discounts",
        channel="Email (automated)",
        kpi="Churn rate",
        save_rate=0.0, upside_rate=0.0, cost_contact=0.03, offer_cost=0.0),
}

PROFILE_COLS = [
    "customer_id", "age", "gender", "region", "country", "is_member", "app_installed",
    "email_subscribed", "top_category", "n_orders", "tenure_days", "recency_days",
    "avg_gap_days", "overdue_ratio", "total_spend", "aov", "orders_last_90d",
    "orders_prev_90d", "return_rate", "email_open_rate", "email_open_rate_3m",
]
PRED_COLS = [
    "p_alive", "churn_risk", "exp_visits_6m", "exp_visits_12m", "pred_aov",
    "clv_6m", "clv_12m", "potential_clv_6m", "potential_clv_12m",
    "revenue_at_risk_6m", "revenue_at_risk_12m", "baseline_6m", "baseline_12m",
]


# ----------------------------------------------------------------------------
# Segment assignment
# ----------------------------------------------------------------------------
def assign_segments(df):
    value_cut = float(df["potential_clv_12m"].quantile(1 - HIGH_VALUE_TOP_SHARE))
    high_value = df["potential_clv_12m"] >= value_cut
    high_risk = df["churn_risk"] >= HIGH_RISK_CUTOFF
    seg = np.select(
        [high_value & high_risk, high_value & ~high_risk, ~high_value & high_risk],
        ["Protect", "Grow", "Win back"], default="Maintain")
    df["segment"] = pd.Categorical(seg, categories=SEGMENT_ORDER)
    return df, value_cut


# ----------------------------------------------------------------------------
# Plain-English reasons and next action for every customer
# ----------------------------------------------------------------------------
def build_reasons(df):
    """Up to three short reasons why a customer looks the way they do."""
    r = pd.DataFrame(index=df.index)
    n = len(df)
    cand = []  # (condition, text, priority) evaluated row-wise below via vector strings

    def text(mask, fn):
        out = np.full(n, "", dtype=object)
        idx = np.nonzero(mask.to_numpy())[0]
        out[idx] = [fn(row) for row in df.iloc[idx].itertuples()]
        return out

    r["a"] = text((df["overdue_ratio"] >= 2) & df["avg_gap_days"].notna(),
                  lambda x: f"Last visit {int(x.recency_days)} days ago, {x.overdue_ratio:.1f}x their usual "
                            f"gap of {x.avg_gap_days:.0f} days")
    r["b"] = text((df["orders_prev_90d"] > df["orders_last_90d"]) & (df["orders_prev_90d"] >= 1),
                  lambda x: f"Visits down: {int(x.orders_prev_90d)} in the previous 90 days, "
                            f"{int(x.orders_last_90d)} in the last 90")
    r["c"] = text((df["n_orders"] == 1) & (df["recency_days"] > 90),
                  lambda x: f"Only one visit, {int(x.recency_days)} days ago")
    r["d"] = text((df["email_subscribed"] == 1) & df["email_open_rate"].notna()
                  & (df["email_open_rate_3m"] < 0.5 * df["email_open_rate"]),
                  lambda x: "Email opens have dropped sharply")
    r["e"] = text(df["return_rate"] >= 0.15, lambda x: f"High return rate ({x.return_rate:.0%})")
    r["f"] = text(df["is_member"] == 0, lambda x: "Not in the loyalty programme")
    positive = text((df["overdue_ratio"] < 1) & (df["orders_last_90d"] >= 2),
                    lambda x: f"Active: {int(x.orders_last_90d)} visits in the last 90 days")
    positive2 = text(df["is_member"] == 1, lambda x: "Loyalty member")
    risky = df["segment"].isin(["Protect", "Win back"]).to_numpy()

    out = []
    for i in range(n):
        if risky[i]:
            parts = [r[c].iat[i] for c in "abcdef" if r[c].iat[i]]
        else:
            parts = [p for p in (positive[i], positive2[i]) if p]
            parts += [r[c].iat[i] for c in "ef" if r[c].iat[i]]
        out.append("; ".join(parts[:3]) if parts else "Steady, regular shopper")
    return out


def build_actions(df):
    cat = df["top_category"].fillna("their favourite category").astype(str)
    seg = df["segment"].astype(str)
    offer = np.select(
        [seg == "Protect", seg == "Grow", seg == "Win back"],
        ["Member early access + offer on " + cat,
         "Loyalty tier upgrade + " + cat + " bundle",
         "Reactivation offer on " + cat],
        default="Seasonal nurture email, no discount")
    return offer


# ----------------------------------------------------------------------------
# Segment summary and campaign economics
# ----------------------------------------------------------------------------
def summarise(df):
    rows = []
    total_clv = df["clv_12m"].sum()
    for s in SEGMENT_ORDER:
        d = df[df["segment"] == s]
        c = CAMPAIGNS[s]
        n = len(d)
        at_risk = d["revenue_at_risk_12m"].sum()
        recovered = at_risk * c["save_rate"] + d["clv_12m"].sum() * c["upside_rate"]
        cost = n * c["cost_contact"] + recovered * c["offer_cost"]
        top_cat = d["top_category"].value_counts().head(3)
        rows.append({
            "segment": s,
            "customers": n,
            "customers_pct": round(n / len(df) * 100, 1),
            "clv_12m_gbp": round(d["clv_12m"].sum()),
            "clv_12m_share_pct": round(d["clv_12m"].sum() / total_clv * 100, 1),
            "clv_6m_gbp": round(d["clv_6m"].sum()),
            "potential_12m_gbp": round(d["potential_clv_12m"].sum()),
            "revenue_at_risk_12m_gbp": round(at_risk),
            "avg_clv_12m_gbp": round(d["clv_12m"].mean(), 1),
            "avg_potential_12m_gbp": round(d["potential_clv_12m"].mean(), 1),
            "avg_churn_risk_pct": round(d["churn_risk"].mean() * 100, 1),
            "loyalty_member_pct": round(d["is_member"].mean() * 100, 1),
            "avg_age": round(d["age"].mean(), 1),
            "avg_orders": round(d["n_orders"].mean(), 1),
            "top_categories": top_cat.index.tolist(),
            "goal": c["goal"], "play": c["play"], "channel": c["channel"], "kpi": c["kpi"],
            "assumptions": {k: c[k] for k in ("save_rate", "upside_rate", "cost_contact", "offer_cost")},
            "expected_gain_gbp": round(recovered),
            "campaign_cost_gbp": round(cost),
            "net_return_gbp": round(recovered - cost),
            "roi": round((recovered - cost) / cost, 2) if (cost > 0 and recovered > 0) else None,
        })
    return rows


def cut_by(df, col, order=None):
    g = df.groupby(col, observed=True).agg(
        customers=("customer_id", "size"), clv_12m=("clv_12m", "sum"),
        avg_clv_12m=("clv_12m", "mean"), revenue_at_risk_12m=("revenue_at_risk_12m", "sum"),
        avg_churn_risk=("churn_risk", "mean")).round(2).reset_index()
    if order:
        g[col] = pd.Categorical(g[col], categories=order, ordered=True)
        g = g.sort_values(col)
    else:
        g = g.sort_values("clv_12m", ascending=False)
    g[col] = g[col].astype(str)
    return g.rename(columns={col: "group"}).to_dict("records")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def run():
    feats = pd.read_parquet(C.OUTPUT_DIR / "features_score.parquet")
    pred = pd.read_parquet(C.OUTPUT_DIR / "predictions_score.parquet")
    df = feats[PROFILE_COLS].merge(pred[["customer_id"] + PRED_COLS], on="customer_id", how="inner")
    assert len(df) == len(feats) == len(pred), "customer lists do not match"

    df, value_cut = assign_segments(df)
    df["why"] = build_reasons(df)
    df["recommended_action"] = build_actions(df)
    df["priority_rank"] = (df.groupby("segment", observed=True)["revenue_at_risk_12m"]
                           .rank(ascending=False, method="first").astype(int))
    df = df.sort_values(["segment", "priority_rank"]).reset_index(drop=True)

    age_band = pd.cut(df["age"], [0, 24, 34, 44, 54, 120],
                      labels=["Under 25", "25-34", "35-44", "45-54", "55+"])
    df["age_band"] = age_band.astype(str)
    df["loyalty_status"] = np.where(df["is_member"] == 1, "Loyalty member", "Not a member")

    summary = summarise(df)
    out = {
        "as_of": "2026-09-30",
        "rules": {"high_value_cutoff_potential_12m_gbp": round(value_cut, 2),
                  "high_value_top_share": HIGH_VALUE_TOP_SHARE,
                  "high_risk_cutoff": HIGH_RISK_CUTOFF},
        "headline": {
            "customers": int(len(df)),
            "clv_6m_gbp": round(df["clv_6m"].sum()),
            "clv_12m_gbp": round(df["clv_12m"].sum()),
            "revenue_at_risk_12m_gbp": round(df["revenue_at_risk_12m"].sum()),
            "baseline_12m_gbp": round(df["baseline_12m"].sum()),
            "expected_gain_gbp": sum(s["expected_gain_gbp"] for s in summary),
            "campaign_cost_gbp": sum(s["campaign_cost_gbp"] for s in summary),
        },
        "segments": summary,
        "cuts": {
            "region": cut_by(df, "region"),
            "country": cut_by(df, "country"),
            "top_category": cut_by(df, "top_category"),
            "age_band": cut_by(df, "age_band", ["Under 25", "25-34", "35-44", "45-54", "55+"]),
            "loyalty_status": cut_by(df, "loyalty_status"),
        },
        "note": "Campaign save rates, costs and offer costs are illustrative assumptions, not Primark data.",
    }
    df.to_parquet(C.OUTPUT_DIR / "customer_segments.parquet", index=False)
    (C.OUTPUT_DIR / "segment_summary.json").write_text(json.dumps(out, indent=2, default=float))
    print_summary(out, df)
    return df, out


def print_summary(out, df):
    h = out["headline"]
    print("\n" + "=" * 86)
    print("CUSTOMER SEGMENTS  (as of 30 Sep 2026, synthetic data)")
    print("=" * 86)
    print(f"  High value = worth GBP {out['rules']['high_value_cutoff_potential_12m_gbp']:.0f}+ over 12 months "
          f"if kept active (top {int(HIGH_VALUE_TOP_SHARE * 100)}%);  high risk = churn risk of "
          f"{int(HIGH_RISK_CUTOFF * 100)}%+\n")
    print(f"  {'segment':<10}{'customers':>10}{'share':>7}{'CLV 12m':>11}{'at risk':>11}"
          f"{'churn':>7}{'member':>8}{'gain':>9}{'cost':>8}{'ROI':>6}")
    for s in out["segments"]:
        roi = f"{s['roi']:.1f}x" if s["roi"] is not None else "-"
        print(f"  {s['segment']:<10}{s['customers']:>10,}{s['customers_pct']:>6.0f}%"
              f"{s['clv_12m_gbp']:>11,}{s['revenue_at_risk_12m_gbp']:>11,}"
              f"{s['avg_churn_risk_pct']:>6.0f}%{s['loyalty_member_pct']:>7.0f}%"
              f"{s['expected_gain_gbp']:>9,}{s['campaign_cost_gbp']:>8,}{roi:>6}")
    print(f"\n  Total predicted 12m CLV GBP {h['clv_12m_gbp']:,}   revenue at risk GBP "
          f"{h['revenue_at_risk_12m_gbp']:,}")
    print(f"  Campaign plan: spend about GBP {h['campaign_cost_gbp']:,} to win back about "
          f"GBP {h['expected_gain_gbp']:,} (assumptions, not data)")
    print("-" * 86)
    print("  Top 3 Protect customers (largest revenue at risk):")
    for r in df[df["segment"] == "Protect"].head(3).itertuples():
        print(f"    {r.customer_id}  at risk GBP {r.revenue_at_risk_12m:.0f}  | {r.why}")
    d = df[df["customer_id"] == f"C{C.DEMO_CUSTOMER_INDEX + 1:05d}"].iloc[0]
    print("-" * 86)
    print(f"  DEMO CUSTOMER {d['customer_id']}: segment = {d['segment']}, priority #{d['priority_rank']} of "
          f"{(df['segment'] == d['segment']).sum():,}")
    print(f"    why: {d['why']}")
    print(f"    action: {d['recommended_action']}")
    print("=" * 86)
    print(f"Saved: customer_segments.parquet, segment_summary.json in {C.OUTPUT_DIR}")


if __name__ == "__main__":
    run()
