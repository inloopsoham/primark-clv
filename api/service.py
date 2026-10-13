"""
service.py - the data logic behind the web app (no web code in here).

It loads the precomputed results once, then answers questions such as
"give me the overview", "show customer C10000", "what if we enrol 20 % more
people in the loyalty programme?". main.py simply exposes these as web
endpoints. Nothing is trained here, so every answer is instant.
"""
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from src import config as C
from src.models import p_alive

OUT = C.OUTPUT_DIR
SEGMENTS = ["Protect", "Grow", "Win back", "Maintain"]
TODAY = C.END_DATE

LIST_COLUMNS = [
    "customer_id", "segment", "priority_rank", "age", "gender", "region", "country", "is_member",
    "top_category", "n_orders", "recency_days", "churn_risk", "clv_12m", "potential_clv_12m",
    "revenue_at_risk_12m", "why", "recommended_action",
]
SORTABLE = {"revenue_at_risk_12m", "clv_12m", "potential_clv_12m", "churn_risk", "recency_days",
            "n_orders", "age", "priority_rank", "customer_id"}


def clean(o):
    """Make anything JSON-safe: numpy -> python, NaN -> None, dates -> text."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if (np.isnan(o) or np.isinf(o)) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.strftime("%Y-%m-%d")
    if o is pd.NaT:
        return None
    return o


def frame_records(df):
    return clean(json.loads(df.to_json(orient="records", date_format="iso")))


class Store:
    def __init__(self):
        needed = ["customer_segments.parquet", "segment_summary.json", "metrics.json",
                  "loyalty_analysis.json", "loyalty_uplift.parquet"]
        missing = [f for f in needed if not (OUT / f).exists()]
        if missing:
            raise RuntimeError("Missing results: " + ", ".join(missing)
                               + ". Run  python run_all.py  first.")
        self.seg = pd.read_parquet(OUT / "customer_segments.parquet")
        self.seg["is_member"] = self.seg["is_member"].astype(int)
        self.index = self.seg.set_index("customer_id", drop=False)
        self.summary = json.loads((OUT / "segment_summary.json").read_text())
        self.metrics = json.loads((OUT / "metrics.json").read_text())
        self.loyalty = json.loads((OUT / "loyalty_analysis.json").read_text())
        self.uplift = pd.read_parquet(OUT / "loyalty_uplift.parquet")
        self.params = json.loads((OUT / "models" / "bgnbd_params.json").read_text())
        self.feature_dict = pd.read_csv(OUT / "feature_dictionary.csv")
        self.demo_id = f"C{C.DEMO_CUSTOMER_INDEX + 1:05d}"
        self._monthly = None

    # ------------------------------------------------------------------ db
    def _con(self):
        return sqlite3.connect(C.DB_PATH)

    # ------------------------------------------------------------ overview
    def monthly_history(self):
        if self._monthly is None:
            con = self._con()
            tx = pd.read_sql(
                "SELECT substr(transaction_date,1,7) AS month, SUM(amount_gbp) AS gross, "
                "COUNT(DISTINCT transaction_id) AS orders, COUNT(DISTINCT customer_id) AS active_customers "
                "FROM transactions GROUP BY month ORDER BY month", con)
            rt = pd.read_sql("SELECT substr(return_date,1,7) AS month, SUM(amount_refunded_gbp) AS refunds "
                             "FROM returns GROUP BY month", con)
            cu = pd.read_sql("SELECT substr(join_date,1,7) AS month, COUNT(*) AS joined FROM customers "
                             "GROUP BY month ORDER BY month", con)
            con.close()
            m = tx.merge(rt, on="month", how="left").fillna({"refunds": 0})
            m["net_sales"] = (m["gross"] - m["refunds"]).round(0)
            m = m.merge(cu, on="month", how="left").fillna({"joined": 0})
            m["identified_customers"] = m["joined"].cumsum().astype(int)
            m["gross"] = m["gross"].round(0)
            self._monthly = frame_records(m[["month", "gross", "net_sales", "orders", "active_customers",
                                             "identified_customers"]])
        return self._monthly

    def overview(self):
        s = self.seg
        h = self.summary["headline"]
        rng = np.random.default_rng(C.SEED)
        sample = s.sample(1800, random_state=C.SEED)[
            ["customer_id", "segment", "potential_clv_12m", "churn_risk", "clv_12m"]].copy()
        sample["segment"] = sample["segment"].astype(str)
        cap = float(s["clv_12m"].quantile(0.99))
        counts, edges = np.histogram(s["clv_12m"].clip(upper=cap), bins=20)
        cc, ce = np.histogram(s["churn_risk"], bins=10, range=(0, 1))
        sc = {(r["horizon"], r["model_key"]): r for r in self.metrics["scorecard"]}
        final = self.metrics["final_model"]
        return clean({
            "as_of": self.summary["as_of"],
            "rules": self.summary["rules"],
            "headline": h,
            "segments": self.summary["segments"],
            "monthly": self.monthly_history(),
            "clv_histogram": [{"from": round(edges[i], 1), "to": round(edges[i + 1], 1), "customers": int(counts[i])}
                              for i in range(len(counts))],
            "churn_histogram": [{"from": round(ce[i], 1), "to": round(ce[i + 1], 1), "customers": int(cc[i])}
                                for i in range(len(cc))],
            "scatter": frame_records(sample),
            "model_headline": {
                "final_model": self.metrics["final_model_name"],
                "mae_12m": sc[("12m", final)]["mae_gbp"],
                "baseline_mae_12m": sc[("12m", "baseline")]["mae_gbp"],
                "bias_pct_12m": sc[("12m", final)]["total_bias_pct"],
                "baseline_bias_pct_12m": sc[("12m", "baseline")]["total_bias_pct"],
                "rfm_mae_12m": sc[("12m", "rfm")]["mae_gbp"],
                "rfm_bias_pct_12m": sc[("12m", "rfm")]["total_bias_pct"],
                "churn_auc": self.metrics["churn"]["auc_bgnbd"],
            },
            "loyalty_headline": {
                "members_pct": self.loyalty["members"]["customers_pct"],
                "members_clv_share_pct": self.loyalty["members"]["clv_12m_share_pct"],
                "visit_rate_ratio": self.loyalty["behaviour"]["visit_rate_ratio"],
                "leave_rate_ratio": self.loyalty["behaviour"]["leave_rate_ratio"],
            },
            "demo_customer_id": self.demo_id,
        })

    # ------------------------------------------------------------ segments
    def segments(self):
        return clean({"rules": self.summary["rules"], "segments": self.summary["segments"],
                      "cuts": self.summary["cuts"], "note": self.summary["note"]})

    # ----------------------------------------------------------- customers
    def list_customers(self, segment=None, region=None, member=None, q=None,
                       sort="revenue_at_risk_12m", descending=True, limit=25, offset=0):
        d = self.seg
        if segment:
            d = d[d["segment"].astype(str) == segment]
        if region:
            d = d[d["region"] == region]
        if member is not None:
            d = d[d["is_member"] == int(member)]
        if q:
            d = d[d["customer_id"].str.contains(q.strip().upper(), regex=False)]
        if sort not in SORTABLE:
            sort = "revenue_at_risk_12m"
        d = d.sort_values(sort, ascending=not descending)
        total = len(d)
        page = d.iloc[offset: offset + max(1, min(limit, 200))][LIST_COLUMNS].copy()
        page["segment"] = page["segment"].astype(str)
        return {"total": int(total), "offset": int(offset), "rows": frame_records(page)}

    def customer(self, cid):
        cid = cid.strip().upper()
        if cid not in self.index.index:
            return None
        r = self.index.loc[cid]
        con = self._con()
        lines = pd.read_sql(
            "SELECT transaction_id, transaction_date AS date, store_id, category, quantity, amount_gbp "
            "FROM transactions WHERE customer_id = ? ORDER BY transaction_date", con, params=(cid,))
        rets = pd.read_sql(
            "SELECT return_date AS date, category, amount_refunded_gbp AS refunded, reason "
            "FROM returns WHERE customer_id = ? ORDER BY return_date", con, params=(cid,))
        con.close()

        orders = (lines.groupby("transaction_id", sort=False)
                  .agg(date=("date", "first"), store_id=("store_id", "first"),
                       amount=("amount_gbp", "sum"), items=("quantity", "sum"),
                       categories=("category", lambda s: ", ".join(sorted(set(s)))))
                  .reset_index())
        orders["amount"] = orders["amount"].round(2)
        orders["date_ts"] = pd.to_datetime(orders["date"])
        orders["gap_days"] = orders["date_ts"].diff().dt.days
        monthly = (orders.assign(month=orders["date_ts"].dt.strftime("%Y-%m"))
                   .groupby("month").agg(spend=("amount", "sum"), visits=("amount", "size")).round(2).reset_index())
        cats = lines.groupby("category")["amount_gbp"].sum().sort_values(ascending=False).round(2)

        # How the model's belief "still active?" changed week by week
        first = orders["date_ts"].iloc[0]
        vis_days = (orders["date_ts"] - first).dt.days.to_numpy()
        grid = np.arange(int(vis_days[0]) + 7, (TODAY - first).days + 1, 7)
        if len(grid) == 0 or grid[-1] != (TODAY - first).days:
            grid = np.append(grid, (TODAY - first).days)
        n_seen = np.searchsorted(vis_days, grid, side="right")
        x = (n_seen - 1).astype(float)
        last = vis_days[np.maximum(n_seen - 1, 0)]
        pa = p_alive(self.params, x, last / 7.0, grid / 7.0)
        trajectory = [{"date": (first + pd.Timedelta(days=int(g))).strftime("%Y-%m-%d"),
                       "p_alive": round(float(p), 4)} for g, p in zip(grid, pa)]

        seg_name = str(r["segment"])
        peers = self.seg[self.seg["segment"].astype(str) == seg_name]
        up = self.uplift[self.uplift["customer_id"] == cid]
        profile_keys = ["customer_id", "age", "gender", "region", "country", "is_member", "app_installed",
                        "email_subscribed", "top_category", "n_orders", "tenure_days", "recency_days",
                        "avg_gap_days", "overdue_ratio", "total_spend", "aov", "orders_last_90d",
                        "orders_prev_90d", "return_rate", "email_open_rate", "email_open_rate_3m"]
        pred_keys = ["p_alive", "churn_risk", "exp_visits_6m", "exp_visits_12m", "pred_aov", "clv_6m",
                     "clv_12m", "potential_clv_6m", "potential_clv_12m", "revenue_at_risk_6m",
                     "revenue_at_risk_12m", "baseline_6m", "baseline_12m"]
        return clean({
            "customer_id": cid,
            "segment": seg_name,
            "priority_rank": int(r["priority_rank"]),
            "segment_size": int(len(peers)),
            "why": r["why"],
            "recommended_action": r["recommended_action"],
            "play": next(s["play"] for s in self.summary["segments"] if s["segment"] == seg_name),
            "channel": next(s["channel"] for s in self.summary["segments"] if s["segment"] == seg_name),
            "profile": {k: r[k] for k in profile_keys},
            "prediction": {k: r[k] for k in pred_keys},
            "peer_average": {"clv_12m": peers["clv_12m"].mean(), "churn_risk": peers["churn_risk"].mean(),
                             "n_orders": peers["n_orders"].mean(), "aov": peers["aov"].mean()},
            "loyalty_uplift_12m_gbp": float(up["uplift_gbp_12m"].iloc[0]) if len(up) else None,
            "orders": frame_records(orders[["date", "store_id", "amount", "items", "categories", "gap_days"]]),
            "monthly": frame_records(monthly),
            "categories": [{"category": k, "spend": float(v)} for k, v in cats.items()],
            "returns": frame_records(rets),
            "alive_trajectory": trajectory,
            "summary": self._sentence(r, seg_name),
        })

    @staticmethod
    def _sentence(r, seg):
        base = (f"{r['customer_id']} is in the {seg} segment: {r['churn_risk']:.0%} chance of having "
                f"drifted away, and worth about £{r['potential_clv_12m']:.0f} over the next 12 months if kept active.")
        if seg == "Protect":
            return base + f" Expected value is only £{r['clv_12m']:.0f} today, so about £{r['revenue_at_risk_12m']:.0f} is at risk."
        if seg == "Grow":
            return base + " Healthy and valuable: reward and deepen the relationship."
        return base

    # --------------------------------------------------------------- model
    def table_counts(self):
        con = self._con()
        out = {t: int(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
               for t in ("customers", "transactions", "returns", "loyalty", "email_engagement")}
        con.close()
        return out

    def model_info(self):
        m = dict(self.metrics)
        return clean({**m, "feature_dictionary": frame_records(self.feature_dict),
                      "tables": self.table_counts(),
                      "data_summary": {"customers": int(len(self.seg)), "as_of": self.summary["as_of"],
                                       "synthetic": True}})

    # ------------------------------------------------------------- loyalty
    def loyalty_info(self):
        return clean(self.loyalty)

    def simulate(self, enrol_pct=20.0, causal_share=0.5, cost_per_enrolment=1.5, targeting="targeted"):
        enrol_pct = float(np.clip(enrol_pct, 0, 100))
        causal_share = float(np.clip(causal_share, 0, 1))
        cost = float(max(cost_per_enrolment, 0))
        gains = self.uplift["uplift_gbp_12m"].to_numpy()        # already sorted, best first
        n, total = len(gains), float(gains.sum())
        cum = np.concatenate([[0.0], np.cumsum(gains)])

        def scenario(pct, mode):
            k = int(round(n * pct / 100))
            full = float(cum[k]) if mode == "targeted" else total * pct / 100
            gain = full * causal_share
            spend = k * cost
            return {"enrolled": k, "extra_clv_gbp": round(gain), "cost_gbp": round(spend),
                    "net_gbp": round(gain - spend), "roi": round((gain - spend) / spend, 2) if spend > 0 else None}

        curve = []
        for pct in range(0, 101, 5):
            t, r = scenario(pct, "targeted"), scenario(pct, "random")
            curve.append({"enrol_pct": pct, "targeted_net_gbp": t["net_gbp"], "random_net_gbp": r["net_gbp"],
                          "targeted_gain_gbp": t["extra_clv_gbp"], "random_gain_gbp": r["extra_clv_gbp"]})
        best = max(curve, key=lambda c: c["targeted_net_gbp"])
        return clean({
            "inputs": {"enrol_pct": enrol_pct, "causal_share": causal_share,
                       "cost_per_enrolment_gbp": cost, "targeting": targeting},
            "non_members": n,
            "result": scenario(enrol_pct, targeting if targeting in ("targeted", "random") else "targeted"),
            "targeted": scenario(enrol_pct, "targeted"),
            "random": scenario(enrol_pct, "random"),
            "best_targeted_enrol_pct": best["enrol_pct"],
            "best_targeted_net_gbp": best["targeted_net_gbp"],
            "curve": curve,
            "note": "Association, not proof of cause: the 'causal share' says how much of the member/"
                    "non-member gap you believe the programme itself creates. Cost per enrolment is an assumption.",
        })
