"""
generate_data.py - Stage 1: build the synthetic Primark-style dataset.

What it creates (5 tables, all synthetic):
  customers         one row per identified customer (age, location, join date)
  transactions      one row per category bought in a visit (what, how much, where)
  returns           items brought back
  loyalty           loyalty / app programme membership
  email_engagement  monthly emails sent / opened / clicked

How the "shopping behaviour" is simulated (plain English):
  - Every customer has their own visit rate (some shop weekly, some a few
    times a year) and their own chance of quietly leaving after each visit.
    This is the classic BG/NBD story that our Stage 3 model will try to recover.
  - Visits are more likely on weekends and in busy months
    (summer, back-to-school, Christmas).
  - Each customer has favourite categories and a typical price level.
  - Loyalty members visit a bit more often and leave a bit less often
    (an assumption we state openly; it powers the uplift simulator later).

Run from the project root:   python -m src.generate_data
"""
import sqlite3
import time

import numpy as np
import pandas as pd

from src import config as C


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def day_to_date(day_idx):
    """Convert 'days since START_DATE' into real dates."""
    return C.START_DATE + pd.to_timedelta(np.asarray(day_idx), unit="D")


def visit_seasonality():
    """How busy each day of the window is (average = 1.0)."""
    days = pd.date_range(C.START_DATE, C.END_DATE, freq="D")
    month_f = np.array(C.MONTH_VISITS)[days.month.to_numpy() - 1]
    dow_f = np.array(C.WEEKDAY_VISITS)[days.weekday.to_numpy()]
    f = month_f * dow_f
    return f / f.mean()


def category_month_multipliers():
    """12 x 8 table: how much each category is boosted in each month."""
    m = np.ones((12, len(C.CATEGORIES)))
    for month, boosts in C.CATEGORY_SEASON.items():
        for cat_idx, mult in boosts.items():
            m[month - 1, cat_idx] = mult
    return m


# ----------------------------------------------------------------------------
# 1. Customers (who they are + hidden behaviour traits)
# ----------------------------------------------------------------------------
def make_customers(rng):
    n = C.N_CUSTOMERS
    names = list(C.PERSONAS)
    spec = [C.PERSONAS[k] for k in names]
    persona_idx = rng.choice(len(names), n, p=[s["weight"] for s in spec])

    def per_persona(key):  # look up a persona setting for every customer
        return np.array([s[key] for s in spec])[persona_idx]

    # --- demographics
    age_mean = np.array([s["age"][0] for s in spec])[persona_idx]
    age_sd = np.array([s["age"][1] for s in spec])[persona_idx]
    age = np.clip(np.round(rng.normal(age_mean, age_sd)), 16, 82).astype(int)

    p_f = per_persona("female")
    u = rng.random(n)
    gender = np.where(u < p_f, "F", np.where(u < p_f + (1 - p_f) * 0.95, "M", "X"))

    # --- location: region first, then a home store inside that region
    regions = list(C.REGION_WEIGHTS)
    region = rng.choice(regions, n, p=list(C.REGION_WEIGHTS.values()))
    store_ids = np.array([s[0] for s in C.STORES])
    store_region = np.array([s[4] for s in C.STORES])
    store_w = np.array([s[5] for s in C.STORES])
    home_store_idx = np.zeros(n, dtype=int)
    for r in regions:
        pool = np.where(store_region == r)[0]
        mask = region == r
        home_store_idx[mask] = rng.choice(pool, mask.sum(), p=store_w[pool] / store_w[pool].sum())

    # --- loyalty membership
    is_member = rng.random(n) < per_persona("member")

    # --- hidden behaviour (BG/NBD): visit rate and drop-out chance
    lam_week = rng.gamma(C.LAM_SHAPE, C.LAM_SCALE, n) * per_persona("freq")
    lam_week = np.where(is_member, lam_week * C.LOYALTY_FREQ_UPLIFT, lam_week)
    lam_week = np.clip(lam_week, 0.01, 1.5)
    p_drop = rng.beta(C.DROP_A, C.DROP_B, n)
    p_drop = np.where(is_member, p_drop * C.LOYALTY_CHURN_FACTOR, p_drop)
    p_drop = np.clip(p_drop, 0.01, 0.8)

    # --- when they were first identified (a little skewed towards the launch)
    join_day = np.floor(rng.beta(1.0, 1.2, n) * (C.N_DAYS - 21)).astype(int)

    # --- spending style
    price_level = rng.lognormal(0, 0.20, n)
    return_mult = rng.gamma(1.2, 1 / 1.2, n)

    # --- email habits
    open_base = rng.beta(2.0, 4.67, n) * np.clip((lam_week / lam_week.mean()) ** 0.15, 0.7, 1.4)
    click_base = rng.beta(1.5, 10.0, n)
    subscribed = rng.random(n) < np.where(is_member, C.EMAIL_SUBSCRIBE["member"], C.EMAIL_SUBSCRIBE["non_member"])
    app_installed = rng.random(n) < np.where(is_member, C.APP_INSTALLED["member"], C.APP_INSTALLED["non_member"])

    # --- favourite categories (a personal mix drawn around the persona's taste)
    pref = np.zeros((n, len(C.CATEGORIES)))
    gender_mult = {
        "F": np.array([1, 0.4, 1, 1, 1, 1, 1, 1.0]),
        "M": np.array([0.3, 3.0, 1, 1, 0.6, 1, 1, 0.8]),
        "X": np.ones(len(C.CATEGORIES)),
    }
    for p_i, s in enumerate(spec):
        for g in ("F", "M", "X"):
            mask = (persona_idx == p_i) & (gender == g)
            if mask.sum() == 0:
                continue
            alpha = np.array(s["alpha"]) * gender_mult[g] * C.ALPHA_SCALE
            draw = rng.gamma(alpha, size=(mask.sum(), len(alpha))) + 1e-6
            pref[mask] = draw / draw.sum(axis=1, keepdims=True)

    cust = pd.DataFrame({
        "customer_id": [f"C{i + 1:05d}" for i in range(n)],
        "age": age,
        "gender": gender,
        "region": region,
        "home_store_idx": home_store_idx,
        "is_member": is_member,
        "persona": np.array(names)[persona_idx],
        "lam_week": lam_week,
        "p_drop": p_drop,
        "join_day": join_day,
        "price_level": price_level,
        "persona_price": per_persona("price"),
        "lines_extra": per_persona("lines"),
        "return_mult": return_mult,
        "open_base": open_base,
        "click_base": click_base,
        "subscribed": subscribed,
        "app_installed": app_installed,
    })

    # --- the hand-crafted demo customer: loyal family shopper, 38, Manchester
    d = C.DEMO_CUSTOMER_INDEX
    manchester = int(np.where(store_ids == "S03")[0][0])
    demo_values = {
        "age": 38, "gender": "F", "region": "UK", "home_store_idx": manchester,
        "is_member": True, "persona": "Family shopper", "join_day": 13,
        "price_level": 1.15, "persona_price": 1.0, "lines_extra": 1.4,
        "return_mult": 0.7, "open_base": 0.55, "click_base": 0.20,
        "subscribed": True, "app_installed": True,
    }
    for col, val in demo_values.items():
        cust.loc[d, col] = val
    pref[d] = [0.30, 0.08, 0.28, 0.18, 0.05, 0.04, 0.04, 0.03]
    return cust, pref


# ----------------------------------------------------------------------------
# 2. Visits (which days each customer shops)
# ----------------------------------------------------------------------------
def demo_visit_days(rng):
    """Demo customer: a visit every ~18 days, then the gaps stretch out."""
    slip_start = (pd.Timestamp("2026-01-01") - C.START_DATE).days
    last_allowed = (pd.Timestamp("2026-07-20") - C.START_DATE).days
    d, days = 13, [13]
    while True:
        gap = 18 + 0.35 * max(0, d - slip_start) + rng.normal(0, 3)
        d += max(5, int(round(gap)))
        if d > last_allowed:
            break
        days.append(d)
    return np.array(days)


def simulate_visits(rng, cust, f):
    """Return one row per visit: (customer index, day index), and the day each
    customer who left was last seen (-1 = still active)."""
    n = len(cust)
    f_max = f.max()
    lam_day = cust["lam_week"].to_numpy() / 7.0
    p_drop = cust["p_drop"].to_numpy()
    join_day = cust["join_day"].to_numpy().astype(int)
    left_day = np.full(n, -1)
    out_c, out_d = [], []

    for i in range(n):
        if i == C.DEMO_CUSTOMER_INDEX:
            days = demo_visit_days(rng)
            left_day[i] = days[-1]
        else:
            start = join_day[i]
            rate = lam_day[i] * f_max               # candidate visit rate
            k = int(rate * (C.N_DAYS - start) * 1.3) + 10
            t = start + np.cumsum(rng.exponential(1 / rate, k))
            while t[-1] < C.N_DAYS:                 # make sure we cover the window
                t = np.concatenate([t, t[-1] + np.cumsum(rng.exponential(1 / rate, k))])
            d = np.floor(t[t < C.N_DAYS]).astype(int)
            d = d[rng.random(len(d)) < f[d] / f_max]  # busy days keep more visits
            d = np.unique(d)
            d = d[d > start]
            days = np.concatenate([[start], d])      # first visit = join day
            n_visits_before_leaving = rng.geometric(p_drop[i])
            if n_visits_before_leaving <= len(days):
                left_day[i] = days[n_visits_before_leaving - 1]
            days = days[:n_visits_before_leaving]
        out_c.append(np.full(len(days), i))
        out_d.append(days)

    visits = pd.DataFrame({"cust_idx": np.concatenate(out_c), "day": np.concatenate(out_d)})
    visits = visits.sort_values(["day", "cust_idx"], kind="stable").reset_index(drop=True)
    visits["date"] = day_to_date(visits["day"])
    visits["transaction_id"] = [f"T{i + 1:07d}" for i in range(len(visits))]
    return visits, left_day


def assign_stores(rng, visits, cust):
    """85 % of visits go to the home store, the rest to another store in the region."""
    store_ids = np.array([s[0] for s in C.STORES])
    store_region = np.array([s[4] for s in C.STORES])
    store_w = np.array([s[5] for s in C.STORES])
    ci = visits["cust_idx"].to_numpy()
    store_idx = cust["home_store_idx"].to_numpy().astype(int)[ci]
    away = rng.random(len(visits)) > C.HOME_STORE_SHARE
    cust_region = cust["region"].to_numpy()[ci]
    for r in C.REGION_WEIGHTS:
        pool = np.where(store_region == r)[0]
        m = away & (cust_region == r)
        store_idx[m] = rng.choice(pool, m.sum(), p=store_w[pool] / store_w[pool].sum())
    visits["store_id"] = store_ids[store_idx]
    return visits


# ----------------------------------------------------------------------------
# 3. Basket lines (what was bought in each visit)
# ----------------------------------------------------------------------------
def build_transactions(rng, visits, cust, pref):
    ci = visits["cust_idx"].to_numpy()
    month = visits["date"].dt.month.to_numpy()                      # 1..12
    n_lines = np.minimum(1 + rng.poisson(cust["lines_extra"].to_numpy()[ci]), 5)

    # choose which categories are in each basket (weighted, no repeats)
    weights = pref[ci] * category_month_multipliers()[month - 1]
    keys = np.log(weights + 1e-12) - np.log(-np.log(rng.random(weights.shape)))
    ranks = np.argsort(np.argsort(-keys, axis=1), axis=1)
    order_i, cat_i = np.nonzero(ranks < n_lines[:, None])

    qty = 1 + rng.poisson(np.array(C.QTY_EXTRA)[cat_i])
    line_c = ci[order_i]
    unit = (np.array(C.PRICE_MEAN)[cat_i]
            * rng.lognormal(0, 0.35, len(order_i))
            * cust["price_level"].to_numpy()[line_c]
            * cust["persona_price"].to_numpy()[line_c]
            * np.array(C.MONTH_BASKET)[month[order_i] - 1])
    amount = np.round(np.maximum(qty * unit, 0.5), 2)

    tx = pd.DataFrame({
        "transaction_id": visits["transaction_id"].to_numpy()[order_i],
        "customer_id": cust["customer_id"].to_numpy()[line_c],
        "transaction_date": visits["date"].to_numpy()[order_i],
        "store_id": visits["store_id"].to_numpy()[order_i],
        "category": np.array(C.CATEGORIES)[cat_i],
        "quantity": qty,
        "amount_gbp": amount,
    })
    tx.insert(0, "line_id", [f"L{i + 1:08d}" for i in range(len(tx))])
    return tx, line_c


def build_returns(rng, tx, line_c, cust):
    cat_i = tx["category"].map({c: i for i, c in enumerate(C.CATEGORIES)}).to_numpy()
    p_ret = np.array(C.RETURN_RATE)[cat_i] * cust["return_mult"].to_numpy()[line_c]
    returned = rng.random(len(tx)) < p_ret
    r = tx[returned].copy()
    lag = np.minimum(1 + rng.geometric(0.12, len(r)), 30)
    r["return_date"] = r["transaction_date"] + pd.to_timedelta(lag, unit="D")
    r = r[r["return_date"] <= C.END_DATE].copy()
    r["amount_refunded_gbp"] = np.round(r["amount_gbp"] * rng.uniform(0.4, 1.0, len(r)), 2)
    reasons = ["Wrong size", "Changed mind", "Faulty item", "Not as described", "Gift return"]
    r["reason"] = rng.choice(reasons, len(r), p=[0.38, 0.30, 0.12, 0.12, 0.08])
    r = r.sort_values("return_date").reset_index(drop=True)
    r.insert(0, "return_id", [f"R{i + 1:07d}" for i in range(len(r))])
    return r[["return_id", "line_id", "transaction_id", "customer_id", "return_date",
              "category", "amount_refunded_gbp", "reason"]]


# ----------------------------------------------------------------------------
# 4. Loyalty and email
# ----------------------------------------------------------------------------
def build_loyalty(rng, cust):
    n = len(cust)
    member = cust["is_member"].to_numpy().astype(bool)
    enroll_day = np.minimum(cust["join_day"].to_numpy().astype(int) + rng.integers(0, 120, n),
                            C.N_DAYS - 1)
    enroll_date = day_to_date(enroll_day).strftime("%Y-%m-%d").to_numpy()
    return pd.DataFrame({
        "customer_id": cust["customer_id"],
        "is_member": member.astype(int),
        "enrollment_date": np.where(member, enroll_date, None),
        "app_installed": cust["app_installed"].to_numpy().astype(int),
    })


def build_email(rng, cust, left_day):
    months = pd.date_range(C.START_DATE, C.END_DATE, freq="MS")
    n_m = len(months)
    month_start_day = np.array((months - C.START_DATE).days)
    jd = day_to_date(cust["join_day"].to_numpy().astype(int))
    first_m = (jd.year.to_numpy() - C.START_DATE.year) * 12 + (jd.month.to_numpy() - C.START_DATE.month)

    sel = np.nonzero(cust["subscribed"].to_numpy().astype(bool))[0]
    counts = n_m - first_m[sel]
    c_rep = np.repeat(sel, counts)
    offs = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
    m_idx = np.repeat(first_m[sel], counts) + offs

    sent = 3 + rng.poisson(3, len(c_rep))
    open_rate = cust["open_base"].to_numpy().astype(float)[c_rep]
    gone = left_day[c_rep]
    # customers who have drifted away open far fewer emails
    faded = (gone >= 0) & (month_start_day[m_idx] > gone + 30)
    open_rate = np.where(faded, open_rate * 0.5, open_rate)
    opened = rng.binomial(sent, np.clip(open_rate, 0, 1))
    clicked = rng.binomial(opened, np.clip(cust["click_base"].to_numpy().astype(float)[c_rep], 0, 1))
    return pd.DataFrame({
        "customer_id": cust["customer_id"].to_numpy()[c_rep],
        "month": months[m_idx].strftime("%Y-%m-%d"),
        "emails_sent": sent,
        "emails_opened": opened,
        "emails_clicked": clicked,
    })


# ----------------------------------------------------------------------------
# 4b. Second demo customer (C10001): low value and drifting
# ----------------------------------------------------------------------------
def override_low_demo(customers, tx, returns, loyalty, email, ground_truth):
    """Replace C10001 with a hand-written sale shopper. Done after all random
    draws, so every other customer stays exactly as generated."""
    cid = f"C{C.DEMO_LOW_INDEX + 1:05d}"
    customers.loc[customers["customer_id"] == cid,
                  ["age", "gender", "region", "country", "city", "home_store_id", "join_date"]] = \
        [24, "F", "UK", "United Kingdom", "Leeds", "S06", "2025-05-03"]
    # visits: small, regular trips through 2025 (about every six weeks), then silence after Black Friday
    lines = [  # (date, category, quantity, amount)
        ("2025-05-03", "Womenswear", 1, 6.00),
        ("2025-06-21", "Beauty", 1, 3.50), ("2025-06-21", "Accessories", 1, 2.50),
        ("2025-07-26", "Womenswear", 1, 7.00),
        ("2025-09-06", "Womenswear", 1, 5.50),
        ("2025-10-18", "Accessories", 1, 4.00), ("2025-10-18", "Beauty", 1, 2.00),
        ("2025-11-28", "Womenswear", 1, 8.00),
    ]
    dates = sorted({d for d, *_ in lines})
    tid = {d: f"T{9000001 + i:07d}" for i, d in enumerate(dates)}
    new = pd.DataFrame([{"line_id": f"L{90000001 + i:08d}", "transaction_id": tid[d], "customer_id": cid,
                         "transaction_date": d, "store_id": "S06", "category": c, "quantity": q, "amount_gbp": a}
                        for i, (d, c, q, a) in enumerate(lines)])
    tx = pd.concat([tx[tx["customer_id"] != cid], new[tx.columns]], ignore_index=True)
    ret = pd.DataFrame([{"return_id": "R9000001", "line_id": "L90000004", "transaction_id": tid["2025-07-26"],
                         "customer_id": cid, "return_date": "2025-08-02", "category": "Womenswear",
                         "amount_refunded_gbp": 7.00, "reason": "Wrong size"}])
    returns = pd.concat([returns[returns["customer_id"] != cid], ret[returns.columns]], ignore_index=True)
    loyalty.loc[loyalty["customer_id"] == cid, ["is_member", "enrollment_date", "app_installed"]] = [0, None, 0]
    months = pd.date_range("2025-05-01", C.END_DATE, freq="MS")
    em = pd.DataFrame({"customer_id": cid, "month": months.strftime("%Y-%m-%d"), "emails_sent": 4,
                       "emails_opened": [1 if m < pd.Timestamp("2026-02-01") else 0 for m in months],
                       "emails_clicked": [1 if m == pd.Timestamp("2025-11-01") else 0 for m in months]})
    email = pd.concat([email[email["customer_id"] != cid], em[email.columns]], ignore_index=True)
    ground_truth.loc[ground_truth["customer_id"] == cid,
                     ["persona", "true_visits_per_week", "true_dropout_chance", "left_in_window",
                      "last_visit_before_leaving"]] = ["Young fashion", 0.06, 0.30, 1, "2025-11-28"]
    return customers, tx, returns, loyalty, email, ground_truth


# ----------------------------------------------------------------------------
# 5. Save to SQLite + CSV
# ----------------------------------------------------------------------------
def save_tables(tables):
    C.DATA_DIR.mkdir(exist_ok=True)
    if C.DB_PATH.exists():
        C.DB_PATH.unlink()
    con = sqlite3.connect(C.DB_PATH)
    for name, df in tables.items():
        df.to_csv(C.DATA_DIR / f"{name}.csv", index=False)
        df.to_sql(name, con, index=False, if_exists="replace", chunksize=50_000)
    for name in ("transactions", "returns", "loyalty", "email_engagement"):
        con.execute(f"CREATE INDEX idx_{name}_cust ON {name}(customer_id)")
    con.commit()
    con.close()


def print_summary(tables, ground_truth):
    tx, cu = tables["transactions"], tables["customers"]
    orders = tx.groupby("transaction_id")["amount_gbp"].sum()
    per_cust = tx.groupby("customer_id")["transaction_id"].nunique()
    print("\n" + "=" * 60)
    print("SYNTHETIC DATA SUMMARY (not real Primark data)")
    print("=" * 60)
    for name, df in tables.items():
        print(f"  {name:<18}{len(df):>10,} rows")
    print("-" * 60)
    print(f"  Period                {C.START_DATE.date()} to {C.END_DATE.date()}")
    print(f"  Visits (orders)       {len(orders):,}")
    print(f"  Avg order value       GBP {orders.mean():.2f}  (median {orders.median():.2f})")
    print(f"  Visits per customer   {per_cust.mean():.1f} on average")
    print(f"  Total sales           GBP {tx['amount_gbp'].sum():,.0f}")
    print(f"  Loyalty members       {tables['loyalty']['is_member'].mean():.0%}")
    print(f"  Customers who left    {ground_truth['left_in_window'].mean():.0%} (hidden truth)")
    print(f"  Items returned        {len(tables['returns']) / len(tx):.1%} of lines")
    print("  Sales by region:")
    reg = tx.merge(cu[["customer_id", "region"]], on="customer_id").groupby("region")["amount_gbp"].sum()
    for r, v in (reg / reg.sum()).items():
        print(f"      {r:<10}{v:.0%}")
    demo = tx[tx["customer_id"] == f"C{C.DEMO_CUSTOMER_INDEX + 1:05d}"]
    last = pd.to_datetime(demo["transaction_date"]).max()
    print("-" * 60)
    print(f"  Demo customer C{C.DEMO_CUSTOMER_INDEX + 1:05d}: {demo['transaction_id'].nunique()} visits, "
          f"GBP {demo['amount_gbp'].sum():,.0f} spent, last seen {last.date()} "
          f"({(C.END_DATE - last).days} days ago)")
    low = tx[tx["customer_id"] == f"C{C.DEMO_LOW_INDEX + 1:05d}"]
    print(f"  Demo customer C{C.DEMO_LOW_INDEX + 1:05d}: {low['transaction_id'].nunique()} visits, "
          f"GBP {low['amount_gbp'].sum():,.0f} spent, last seen {low['transaction_date'].max()}")
    print("=" * 60)


# ----------------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------------
def generate():
    t0 = time.time()
    rng = np.random.default_rng(C.SEED)

    print("1/6 Creating customers ...")
    cust, pref = make_customers(rng)
    print("2/6 Simulating visits ...")
    f = visit_seasonality()
    visits, left_day = simulate_visits(rng, cust, f)
    visits = assign_stores(rng, visits, cust)
    print("3/6 Building baskets ...")
    tx, line_c = build_transactions(rng, visits, cust, pref)
    print("4/6 Building returns ...")
    returns = build_returns(rng, tx, line_c, cust)
    print("5/6 Building loyalty and email tables ...")
    loyalty = build_loyalty(rng, cust)
    email = build_email(rng, cust, left_day)

    stores = {s[0]: s for s in C.STORES}
    store_ids = np.array([s[0] for s in C.STORES])
    home = store_ids[cust["home_store_idx"].to_numpy().astype(int)]
    customers = pd.DataFrame({
        "customer_id": cust["customer_id"],
        "age": cust["age"].astype(int),
        "gender": cust["gender"],
        "region": cust["region"],
        "country": [stores[s][3] for s in home],
        "city": [stores[s][2] for s in home],
        "home_store_id": home,
        "join_date": day_to_date(cust["join_day"].to_numpy().astype(int)).strftime("%Y-%m-%d"),
    })

    # Convert dates to plain text so SQLite and CSV stay tidy
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"]).dt.strftime("%Y-%m-%d")
    returns["return_date"] = pd.to_datetime(returns["return_date"]).dt.strftime("%Y-%m-%d")

    # Hidden "answer key" for checking the model later. NEVER used as a feature.
    ground_truth = pd.DataFrame({
        "customer_id": cust["customer_id"],
        "persona": cust["persona"],
        "true_visits_per_week": cust["lam_week"].round(4),
        "true_dropout_chance": cust["p_drop"].round(4),
        "left_in_window": (left_day >= 0).astype(int),
        "last_visit_before_leaving": np.where(left_day >= 0, day_to_date(np.maximum(left_day, 0)).strftime("%Y-%m-%d"), None),
    })

    customers, tx, returns, loyalty, email, ground_truth = override_low_demo(
        customers, tx, returns, loyalty, email, ground_truth)

    tables = {"customers": customers, "transactions": tx, "returns": returns,
              "loyalty": loyalty, "email_engagement": email}
    print("6/6 Saving to SQLite and CSV ...")
    save_tables(tables)
    ground_truth.to_csv(C.DATA_DIR / "_ground_truth_for_validation.csv", index=False)
    print_summary(tables, ground_truth)
    print(f"Done in {time.time() - t0:.1f} seconds. Files are in: {C.DATA_DIR}")
    return tables


if __name__ == "__main__":
    generate()
