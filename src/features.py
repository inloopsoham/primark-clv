"""
features.py - Stage 2: turn the 5 raw tables into ONE ROW PER CUSTOMER.

Models cannot read thousands of receipts, so we summarise each customer's
history into a handful of numbers ("features"): how recently they shopped,
how often, how much they spend, what they buy, how often they return things,
whether they are loyalty members and how they react to emails.

We build the table at three points in time ("snapshots"):

  train  30 Sep 2024  -> features + what REALLY happened in the next 6 / 12 months
  test   30 Sep 2025  -> same, kept aside to prove the model works on the future
  score  30 Sep 2026  -> "today": features only. This is what the dashboard shows.

Rule that keeps us honest: a snapshot only uses information that existed on
its cut-off date. Nothing from the future leaks into the features.

Money note: spend targets are NET of returns (what Primark actually keeps).

Run from the project root:   python -m src.features
"""
import sqlite3

import numpy as np
import pandas as pd

from src import config as C

# ----------------------------------------------------------------------------
# Snapshot dates and prediction horizons
# ----------------------------------------------------------------------------
TEST_CUTOFF = C.HOLDOUT_START - pd.Timedelta(days=1)      # 30 Sep 2025
TRAIN_CUTOFF = TEST_CUTOFF - pd.Timedelta(days=365)       # 30 Sep 2024
SCORE_CUTOFF = C.END_DATE                                 # 30 Sep 2026
SNAPSHOTS = {"train": TRAIN_CUTOFF, "test": TEST_CUTOFF, "score": SCORE_CUTOFF}
HORIZON_DAYS = {"6m": 182, "12m": 365}

CAT_SLUG = {c: c.lower().replace(" & ", "_").replace(" ", "_") for c in C.CATEGORIES}


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------
def load_tables():
    """Read the 5 tables from SQLite and turn text dates into real dates."""
    con = sqlite3.connect(C.DB_PATH)
    t = {n: pd.read_sql(f"SELECT * FROM {n}", con)
         for n in ["customers", "transactions", "returns", "loyalty", "email_engagement"]}
    con.close()
    t["customers"]["join_date"] = pd.to_datetime(t["customers"]["join_date"])
    t["transactions"]["transaction_date"] = pd.to_datetime(t["transactions"]["transaction_date"])
    t["returns"]["return_date"] = pd.to_datetime(t["returns"]["return_date"])
    t["loyalty"]["enrollment_date"] = pd.to_datetime(t["loyalty"]["enrollment_date"])
    t["email_engagement"]["month"] = pd.to_datetime(t["email_engagement"]["month"])
    return t


def build_orders(tx, returns):
    """Collapse basket lines into one row per visit (order)."""
    o = tx.groupby("transaction_id", sort=False).agg(
        customer_id=("customer_id", "first"),
        date=("transaction_date", "first"),
        gross=("amount_gbp", "sum"),
        items=("quantity", "sum"),
        n_lines=("line_id", "size"),
    ).reset_index()
    refunds = returns.groupby("transaction_id")["amount_refunded_gbp"].sum()
    o["refund"] = o["transaction_id"].map(refunds).fillna(0.0)
    o["net"] = o["gross"] - o["refund"]                 # what Primark keeps
    o["is_weekend"] = (o["date"].dt.weekday >= 5).astype(int)
    return o


# ----------------------------------------------------------------------------
# Features for one snapshot date
# ----------------------------------------------------------------------------
def make_features(cutoff, t, orders, with_targets):
    cust, tx, returns = t["customers"], t["transactions"], t["returns"]
    loyalty, email = t["loyalty"], t["email_engagement"]
    day = pd.Timedelta(days=1)

    # Only information known on the cut-off date
    o = orders[orders["date"] <= cutoff]
    lines = tx[tx["transaction_date"] <= cutoff]

    # ---- Recency, frequency, monetary (RFM) + tenure
    g = o.groupby("customer_id")
    f = g.agg(first_order=("date", "min"), last_order=("date", "max"),
              n_orders=("date", "size"), total_spend=("gross", "sum"),
              aov=("gross", "mean"), aov_std=("gross", "std"),
              max_order_value=("gross", "max"), avg_items_per_order=("items", "mean"),
              avg_lines_per_order=("n_lines", "mean"), weekend_share=("is_weekend", "mean"))
    f["aov_std"] = f["aov_std"].fillna(0)
    f["tenure_days"] = (cutoff - f["first_order"]).dt.days
    f["recency_days"] = (cutoff - f["last_order"]).dt.days
    span_days = (f["last_order"] - f["first_order"]).dt.days
    f["avg_gap_days"] = np.where(f["n_orders"] > 1, span_days / (f["n_orders"] - 1).clip(lower=1), np.nan)
    f["overdue_ratio"] = f["recency_days"] / f["avg_gap_days"]     # >1 = later than usual

    # Inputs the BG/NBD model needs (measured in weeks)
    f["bgnbd_frequency"] = f["n_orders"] - 1
    f["bgnbd_recency_weeks"] = span_days / 7.0
    f["bgnbd_T_weeks"] = f["tenure_days"] / 7.0

    # ---- Recent momentum
    def window(a, b):  # visits in the period (cutoff - a days, cutoff - b days]
        m = (o["date"] > cutoff - a * day) & (o["date"] <= cutoff - b * day)
        w = o[m].groupby("customer_id")
        return w.size(), w["gross"].sum()
    n90, s90 = window(90, 0)
    n180, s180 = window(180, 0)
    p90, _ = window(180, 90)
    f["orders_last_90d"] = n90
    f["orders_prev_90d"] = p90
    f["orders_last_180d"] = n180
    f["spend_last_90d"] = s90
    f["spend_last_180d"] = s180
    for c in ["orders_last_90d", "orders_prev_90d", "orders_last_180d", "spend_last_90d", "spend_last_180d"]:
        f[c] = f[c].fillna(0)
    f["order_trend"] = f["orders_last_90d"] - f["orders_prev_90d"]   # negative = slowing down

    # ---- Category affinity
    cat = lines.pivot_table(index="customer_id", columns="category", values="amount_gbp",
                            aggfunc="sum", fill_value=0)
    share = cat.div(cat.sum(axis=1), axis=0)
    share.columns = [f"share_{CAT_SLUG[c]}" for c in share.columns]
    f = f.join(share)
    f["top_category"] = cat.idxmax(axis=1)
    f["n_categories"] = (cat > 0).sum(axis=1)

    # ---- Returns
    r = returns[returns["return_date"] <= cutoff]
    n_lines = lines.groupby("customer_id").size()
    f["return_rate"] = (r.groupby("customer_id").size() / n_lines).reindex(f.index).fillna(0)
    f["refund_ratio"] = (r.groupby("customer_id")["amount_refunded_gbp"].sum() / f["total_spend"]).fillna(0)

    # ---- Loyalty (a member only counts once enrolled by the cut-off date)
    ly = loyalty.set_index("customer_id")
    enrolled = (ly["is_member"] == 1) & (ly["enrollment_date"] <= cutoff)
    f["is_member"] = enrolled.reindex(f.index).astype(int)
    months_in = (cutoff - ly["enrollment_date"]).dt.days / 30.4
    f["months_in_programme"] = months_in.where(enrolled, 0).reindex(f.index).clip(lower=0)
    f["app_installed"] = ly["app_installed"].reindex(f.index)

    # ---- Email engagement (only months that had started by the cut-off)
    e = email[email["month"] <= cutoff]
    eg = e.groupby("customer_id")[["emails_sent", "emails_opened", "emails_clicked"]].sum()
    e3 = e[e["month"] > cutoff - 92 * day].groupby("customer_id")[["emails_sent", "emails_opened"]].sum()
    f["email_subscribed"] = f.index.isin(eg.index).astype(int)
    f["email_open_rate"] = (eg["emails_opened"] / eg["emails_sent"]).reindex(f.index)
    f["email_click_rate"] = (eg["emails_clicked"] / eg["emails_opened"].replace(0, np.nan)).reindex(f.index)
    f["email_open_rate_3m"] = (e3["emails_opened"] / e3["emails_sent"]).reindex(f.index)

    # ---- Demographics
    d = cust.set_index("customer_id")[["age", "gender", "region", "country"]]
    f = f.join(d)

    # ---- What REALLY happened next (only for train / test snapshots)
    if with_targets:
        for name, days in HORIZON_DAYS.items():
            m = (orders["date"] > cutoff) & (orders["date"] <= cutoff + days * day)
            w = orders[m].groupby("customer_id")
            visits = w.size().reindex(f.index).fillna(0)
            net = w["net"].sum().reindex(f.index).fillna(0)
            f[f"target_visits_{name}"] = visits
            f[f"target_spend_{name}"] = net.round(2)
            if name == "12m":
                f["target_aov_12m"] = (net / visits.replace(0, np.nan)).round(2)

    f.insert(0, "snapshot_date", cutoff.strftime("%Y-%m-%d"))
    return f.reset_index()


# ----------------------------------------------------------------------------
# Feature dictionary (feeds the analyst page later)
# ----------------------------------------------------------------------------
def feature_dictionary(columns):
    d = {
        "customer_id": ("Identity", "Unique customer id"),
        "snapshot_date": ("Identity", "Date the features were measured (nothing later is used)"),
        "first_order": ("Recency/Frequency", "Date of the customer's first visit"),
        "last_order": ("Recency/Frequency", "Date of the customer's most recent visit"),
        "n_orders": ("Recency/Frequency", "Number of visits up to the snapshot date"),
        "recency_days": ("Recency/Frequency", "Days since the last visit"),
        "tenure_days": ("Recency/Frequency", "Days since the first visit"),
        "avg_gap_days": ("Recency/Frequency", "Average days between visits"),
        "overdue_ratio": ("Recency/Frequency", "Days since last visit divided by usual gap (above 1 = later than usual)"),
        "total_spend": ("Spend", "Total spend before returns (GBP)"),
        "aov": ("Spend", "Average order value (GBP)"),
        "aov_std": ("Spend", "How much order value varies (GBP)"),
        "max_order_value": ("Spend", "Largest single order (GBP)"),
        "avg_items_per_order": ("Spend", "Average items per visit"),
        "avg_lines_per_order": ("Spend", "Average categories per visit"),
        "weekend_share": ("Spend", "Share of visits on Saturday or Sunday"),
        "bgnbd_frequency": ("BG/NBD inputs", "Repeat visits (visits minus 1)"),
        "bgnbd_recency_weeks": ("BG/NBD inputs", "Weeks between first and last visit"),
        "bgnbd_T_weeks": ("BG/NBD inputs", "Weeks between first visit and the snapshot date"),
        "orders_last_90d": ("Momentum", "Visits in the last 90 days"),
        "orders_prev_90d": ("Momentum", "Visits in the 90 days before that"),
        "orders_last_180d": ("Momentum", "Visits in the last 180 days"),
        "spend_last_90d": ("Momentum", "Spend in the last 90 days (GBP)"),
        "spend_last_180d": ("Momentum", "Spend in the last 180 days (GBP)"),
        "order_trend": ("Momentum", "Visits last 90 days minus previous 90 days (negative = slowing)"),
        "top_category": ("Category affinity", "Category with the highest spend"),
        "n_categories": ("Category affinity", "Number of different categories bought"),
        "return_rate": ("Returns", "Share of purchased lines that were returned"),
        "refund_ratio": ("Returns", "Refunds as a share of total spend"),
        "is_member": ("Loyalty", "1 if enrolled in the loyalty programme by the snapshot date"),
        "months_in_programme": ("Loyalty", "Months since enrolment"),
        "app_installed": ("Loyalty", "1 if the customer has the app"),
        "email_subscribed": ("Email", "1 if the customer receives marketing emails"),
        "email_open_rate": ("Email", "Share of emails opened (all time)"),
        "email_click_rate": ("Email", "Share of opened emails that were clicked"),
        "email_open_rate_3m": ("Email", "Share of emails opened in the last 3 months"),
        "age": ("Demographics", "Age in years (synthetic)"),
        "gender": ("Demographics", "F / M / X (synthetic)"),
        "region": ("Demographics", "UK / Ireland / Europe"),
        "country": ("Demographics", "Home country of the customer's main store"),
        "target_visits_6m": ("Target (what happened next)", "Visits in the next 6 months"),
        "target_visits_12m": ("Target (what happened next)", "Visits in the next 12 months"),
        "target_spend_6m": ("Target (what happened next)", "Net spend in the next 6 months (GBP)"),
        "target_spend_12m": ("Target (what happened next)", "Net spend in the next 12 months (GBP)"),
        "target_aov_12m": ("Target (what happened next)", "Average net order value in the next 12 months (GBP)"),
    }
    for c in C.CATEGORIES:
        d[f"share_{CAT_SLUG[c]}"] = ("Category affinity", f"Share of spend in {c}")
    rows = [(c, *d.get(c, ("Other", ""))) for c in columns]
    return pd.DataFrame(rows, columns=["feature", "group", "description"])


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def build_all():
    C.OUTPUT_DIR.mkdir(exist_ok=True)
    print("Loading tables from SQLite ...")
    t = load_tables()
    orders = build_orders(t["transactions"], t["returns"])
    print(f"  {len(orders):,} visits from {orders['customer_id'].nunique():,} customers")

    out = {}
    for name, cutoff in SNAPSHOTS.items():
        print(f"Building '{name}' snapshot (as of {cutoff.date()}) ...")
        feat = make_features(cutoff, t, orders, with_targets=(name != "score"))
        feat.to_parquet(C.OUTPUT_DIR / f"features_{name}.parquet", index=False)
        out[name] = feat

    fd = feature_dictionary(list(out["train"].columns))
    fd.to_csv(C.OUTPUT_DIR / "feature_dictionary.csv", index=False)
    return out


def print_summary(out):
    print("\n" + "=" * 62)
    print("FEATURE TABLES (one row per customer)")
    print("=" * 62)
    for name, f in out.items():
        n_feat = len([c for c in f.columns if not c.startswith("target_")]) - 2
        print(f"  {name:<6} as of {f['snapshot_date'].iloc[0]}   "
              f"{len(f):>7,} customers   {n_feat} features")
    for name in ("train", "test"):
        f = out[name]
        quiet = (f["target_visits_12m"] == 0).mean()
        print("-" * 62)
        print(f"  [{name}] next-12-month reality check")
        print(f"     avg net spend per customer   GBP {f['target_spend_12m'].mean():.2f}")
        print(f"     avg visits per customer      {f['target_visits_12m'].mean():.2f}")
        print(f"     did not return at all        {quiet:.0%}")
        print(f"     correlation: past visits vs future spend   "
              f"{f['bgnbd_frequency'].corr(f['target_spend_12m']):.2f}")
    s = out["score"]
    print("-" * 62)
    print(f"  [score] customers inactive 180+ days: {(s['recency_days'] >= 180).mean():.0%}")
    demo = s[s["customer_id"] == f"C{C.DEMO_CUSTOMER_INDEX + 1:05d}"].iloc[0]
    print(f"  Demo customer {demo['customer_id']}: {int(demo['n_orders'])} visits, "
          f"usual gap {demo['avg_gap_days']:.0f} days,")
    print(f"     last seen {int(demo['recency_days'])} days ago "
          f"(overdue ratio {demo['overdue_ratio']:.1f}x), "
          f"visits last 90 days: {int(demo['orders_last_90d'])}")
    print("=" * 62)
    print(f"Saved to: {C.OUTPUT_DIR}")


if __name__ == "__main__":
    print_summary(build_all())
