"""
loyalty.py - Stage 5a: what is the loyalty / app programme worth?

Question for the board: "If we got more customers into the programme, what
would it be worth?"

How we answer it, in plain English:
  1. Fit the BG/NBD model SEPARATELY for loyalty members and non-members.
     That tells us how differently the two groups behave: how often they visit
     and how quickly they drift away.
  2. For every non-member, ask: "what would this customer's 12-month CLV be if
     they behaved like a typical member?" (same visit history, member behaviour)
     The difference is their modelled loyalty uplift.

IMPORTANT HONESTY NOTE
  Members and non-members differ in other ways too (the people who join may
  already be keener shoppers), so this measures an ASSOCIATION, not proof of
  cause. The simulator therefore lets you choose how much of the gap you
  believe is really caused by the programme (default 50 %).

Run from the project root:   python -m src.loyalty
"""
import json

import numpy as np
import pandas as pd

from src import config as C
from src.models import (HORIZONS, WEEKS, add_bgnbd, bgnbd_inputs, fit_bgnbd,
                        p_alive, visits_if_active)


def expected_visits(params, df, weeks):
    x, tx, T = bgnbd_inputs(df)
    return p_alive(params, x, tx, T) * visits_if_active(params, weeks, x, T)


def group_stats(seg, mask):
    d = seg[mask]
    return {
        "customers": int(len(d)),
        "customers_pct": round(len(d) / len(seg) * 100, 1),
        "avg_clv_12m_gbp": round(float(d["clv_12m"].mean()), 2),
        "clv_12m_total_gbp": round(float(d["clv_12m"].sum())),
        "clv_12m_share_pct": round(float(d["clv_12m"].sum() / seg["clv_12m"].sum() * 100), 1),
        "avg_churn_risk_pct": round(float(d["churn_risk"].mean() * 100), 1),
        "avg_orders": round(float(d["n_orders"].mean()), 1),
        "avg_spend_gbp": round(float(d["total_spend"].mean()), 1),
        "app_installed_pct": round(float(d["app_installed"].mean() * 100), 1),
        "email_subscribed_pct": round(float(d["email_subscribed"].mean() * 100), 1),
    }


def run():
    feats = pd.read_parquet(C.OUTPUT_DIR / "features_score.parquet")
    seg = pd.read_parquet(C.OUTPUT_DIR / "customer_segments.parquet")
    df = feats.merge(seg[["customer_id", "clv_6m", "clv_12m"]], on="customer_id")
    is_m = df["is_member"] == 1

    p_mem = fit_bgnbd(df[is_m])
    p_non = fit_bgnbd(df[~is_m])

    def behaviour(p):
        return {"visits_per_year_if_active": round(52 * p["r"] / p["alpha"], 2),
                "chance_of_leaving_after_each_visit_pct": round(p["a"] / (p["a"] + p["b"]) * 100, 1)}
    beh_m, beh_n = behaviour(p_mem), behaviour(p_non)

    # --- per-customer uplift for non-members (ratio of "as a member" to "as they are")
    non = df[~is_m].copy()
    up = pd.DataFrame({"customer_id": non["customer_id"].to_numpy()})
    for h in HORIZONS:
        as_member = expected_visits(p_mem, non, WEEKS[h])
        as_is = expected_visits(p_non, non, WEEKS[h])
        ratio = np.clip(as_member / np.maximum(as_is, 1e-9), 1.0, 3.0)
        up[f"uplift_ratio_{h}"] = ratio
        up[f"uplift_gbp_{h}"] = non[f"clv_{h}"].to_numpy() * (ratio - 1)
    up = up.sort_values("uplift_gbp_12m", ascending=False).reset_index(drop=True)
    up.to_parquet(C.OUTPUT_DIR / "loyalty_uplift.parquet", index=False)

    # --- curve: value of enrolling the top X % (targeted) vs a random X %
    total = float(up["uplift_gbp_12m"].sum())
    cum = up["uplift_gbp_12m"].cumsum().to_numpy()
    n = len(up)
    curve = []
    for pct in range(0, 101, 5):
        k = int(round(n * pct / 100))
        curve.append({"enrol_pct": pct, "customers": k,
                      "targeted_full_effect_gbp": round(float(cum[k - 1]) if k else 0.0),
                      "random_full_effect_gbp": round(total * pct / 100)})

    out = {
        "as_of": "2026-09-30",
        "members": group_stats(seg, (seg["is_member"] == 1).to_numpy()),
        "non_members": group_stats(seg, (seg["is_member"] == 0).to_numpy()),
        "behaviour": {"members": beh_m, "non_members": beh_n,
                      "visit_rate_ratio": round(beh_m["visits_per_year_if_active"] / beh_n["visits_per_year_if_active"], 2),
                      "leave_rate_ratio": round(beh_m["chance_of_leaving_after_each_visit_pct"]
                                                / beh_n["chance_of_leaving_after_each_visit_pct"], 2)},
        "bgnbd_params": {"members": p_mem, "non_members": p_non},
        "non_member_uplift": {
            "customers": int(n),
            "avg_uplift_12m_gbp": round(total / n, 2),
            "total_uplift_12m_gbp_if_all_enrolled_full_effect": round(total),
            "avg_ratio_12m": round(float(up["uplift_ratio_12m"].mean()), 3),
        },
        "curve": curve,
        "assumptions": {"share_of_gap_that_is_causal_default": 0.5,
                        "cost_per_enrolment_gbp_default": 1.5,
                        "note": "Association, not proof of cause. Cost per enrolment is an illustrative assumption."},
    }
    (C.OUTPUT_DIR / "loyalty_analysis.json").write_text(json.dumps(out, indent=2, default=float))
    print_summary(out)
    return out


def print_summary(o):
    m, n, b, u = o["members"], o["non_members"], o["behaviour"], o["non_member_uplift"]
    print("\n" + "=" * 78)
    print("LOYALTY PROGRAMME VALUE  (synthetic data)")
    print("=" * 78)
    print(f"  {'':<28}{'members':>14}{'non-members':>14}")
    print(f"  {'customers':<28}{m['customers']:>14,}{n['customers']:>14,}")
    print(f"  {'share of predicted CLV':<28}{m['clv_12m_share_pct']:>13.0f}%{n['clv_12m_share_pct']:>13.0f}%")
    print(f"  {'avg 12m CLV (GBP)':<28}{m['avg_clv_12m_gbp']:>14.2f}{n['avg_clv_12m_gbp']:>14.2f}")
    print(f"  {'avg churn risk':<28}{m['avg_churn_risk_pct']:>13.0f}%{n['avg_churn_risk_pct']:>13.0f}%")
    bm, bn = b["members"], b["non_members"]
    print(f"  {'visits / year when active':<28}{bm['visits_per_year_if_active']:>14.1f}{bn['visits_per_year_if_active']:>14.1f}")
    print(f"  {'chance of leaving per visit':<28}{bm['chance_of_leaving_after_each_visit_pct']:>13.1f}%{bn['chance_of_leaving_after_each_visit_pct']:>13.1f}%")
    print(f"\n  Members visit {b['visit_rate_ratio']:.2f}x as often and leave {b['leave_rate_ratio']:.2f}x as quickly.")
    print(f"  If all {u['customers']:,} non-members behaved like members: +GBP "
          f"{u['total_uplift_12m_gbp_if_all_enrolled_full_effect']:,} CLV over 12 months "
          f"(GBP {u['avg_uplift_12m_gbp']:.2f} each) - an upper bound.")
    c = {r["enrol_pct"]: r for r in o["curve"]}
    print(f"  Enrolling the best 20% (targeted) captures GBP {c[20]['targeted_full_effect_gbp']:,} "
          f"vs GBP {c[20]['random_full_effect_gbp']:,} for a random 20%.")
    print("=" * 78)


if __name__ == "__main__":
    run()
