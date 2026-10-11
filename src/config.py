"""
config.py - one place for every setting in the project.

All the other scripts import from here, so if we ever want to change
something (number of customers, dates, seed) we change it once, here.
"""
from pathlib import Path

import pandas as pd

# ----------------------------------------------------------------------------
# Reproducibility: the same seed always produces exactly the same data.
# ----------------------------------------------------------------------------
SEED = 42

# ----------------------------------------------------------------------------
# Folders
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
DB_PATH = DATA_DIR / "primark_clv.db"

# ----------------------------------------------------------------------------
# Size and time window of the synthetic world
# Story: a loyalty / app programme launched on 1 Oct 2023. Every customer in
# the data became "identified" (card, app or email) on their first purchase.
# ----------------------------------------------------------------------------
N_CUSTOMERS = 20_000
START_DATE = pd.Timestamp("2023-10-01")
END_DATE = pd.Timestamp("2026-09-30")          # "today" for the demo
HOLDOUT_START = pd.Timestamp("2025-10-01")     # used in Stage 3 (model test)
N_DAYS = (END_DATE - START_DATE).days + 1

# One hand-crafted customer for the live demo: a high-value shopper whose
# visits are slipping. Index 9999 becomes customer id C10000 (easy to remember).
DEMO_CUSTOMER_INDEX = 9999

# ----------------------------------------------------------------------------
# Product categories (order matters: all arrays below use this order)
# ----------------------------------------------------------------------------
CATEGORIES = [
    "Womenswear", "Menswear", "Kidswear", "Homeware",
    "Beauty", "Accessories", "Footwear", "Sleepwear & Lingerie",
]
# Typical price of one item in GBP
PRICE_MEAN = [8.5, 8.5, 6.0, 7.0, 4.5, 4.5, 10.5, 6.5]
# Average EXTRA items bought in a category on top of the first one
QTY_EXTRA = [0.7, 0.6, 1.3, 0.8, 0.5, 0.5, 0.1, 0.7]
# Share of purchased lines that get returned, by category
RETURN_RATE = [0.08, 0.06, 0.04, 0.03, 0.015, 0.03, 0.07, 0.03]

# Seasonality of spend by month (index 0 = January)
MONTH_BASKET = [0.95, 0.92, 0.97, 1.00, 1.00, 1.02, 1.03, 1.08, 1.05, 1.00, 1.08, 1.20]
# Visit seasonality by month: summer, back-to-school (Aug/Sep), Christmas
MONTH_VISITS = [0.90, 0.85, 0.95, 1.00, 1.00, 1.05, 1.10, 1.30, 1.20, 1.00, 1.20, 1.50]
# Visit seasonality by weekday (Monday first): busy Fri / Sat / Sun
WEEKDAY_VISITS = [0.8, 0.8, 0.8, 0.8, 1.1, 1.5, 1.2]

# Category boosts by month (1-based month -> {category index: multiplier})
CATEGORY_SEASON = {
    6: {0: 1.15, 6: 1.2, 5: 1.2},
    7: {0: 1.15, 6: 1.2, 5: 1.2},
    8: {2: 2.0, 6: 1.3, 1: 1.1, 0: 1.1},     # back-to-school
    9: {2: 1.8, 6: 1.2},
    10: {7: 1.3},
    11: {7: 1.5, 3: 1.3, 5: 1.3, 4: 1.4},    # gifting starts
    12: {4: 1.6, 3: 1.5, 5: 1.5, 7: 1.6, 2: 1.3},  # Christmas
    1: {3: 1.1},
}

# ----------------------------------------------------------------------------
# Customer personas (drive age, favourite categories, basket size)
# alpha = how strongly the persona favours each category (same order as above)
# ----------------------------------------------------------------------------
PERSONAS = {
    "Young fashion":  dict(weight=0.24, age=(24, 4.5), female=0.72, member=0.55,
                           freq=1.00, price=0.95, lines=0.8,
                           alpha=[6, 2, 0.3, 0.8, 2.5, 3, 2.5, 1.5]),
    "Family shopper": dict(weight=0.26, age=(38, 6.0), female=0.78, member=0.45,
                           freq=1.15, price=1.00, lines=1.2,
                           alpha=[3, 2, 5, 2.5, 1, 1, 2, 2]),
    "Value basics":   dict(weight=0.22, age=(34, 11.0), female=0.55, member=0.30,
                           freq=1.00, price=0.90, lines=0.7,
                           alpha=[3, 3, 1.5, 1.5, 0.8, 1, 2.5, 3]),
    "Home & beauty":  dict(weight=0.14, age=(42, 11.0), female=0.85, member=0.50,
                           freq=0.90, price=1.10, lines=0.9,
                           alpha=[2.5, 0.7, 0.7, 5, 4, 2, 1, 2.5]),
    "Mature comfort": dict(weight=0.14, age=(58, 7.0), female=0.65, member=0.35,
                           freq=0.90, price=1.05, lines=0.8,
                           alpha=[3.5, 3, 0.5, 2.5, 1, 1.5, 2.5, 3.5]),
}
ALPHA_SCALE = 0.7   # lower = customers have stronger personal favourites

# ----------------------------------------------------------------------------
# Behaviour model (BG/NBD style, the same family our Stage 3 model uses)
#   lam_week : visits per week while the customer is still "alive"
#   p_drop   : chance the customer quietly leaves after each visit
# ----------------------------------------------------------------------------
LAM_SHAPE, LAM_SCALE = 1.4, 0.085       # mean about 0.12 visits / week
DROP_A, DROP_B = 1.5, 7.5               # mean drop-out chance about 17 %
LOYALTY_FREQ_UPLIFT = 1.20              # members visit 20 % more often
LOYALTY_CHURN_FACTOR = 0.85             # and leave 15 % less often
EMAIL_SUBSCRIBE = {"member": 0.90, "non_member": 0.50}
APP_INSTALLED = {"member": 0.70, "non_member": 0.10}

# ----------------------------------------------------------------------------
# Locations: (store_id, store name, city, country, region, size weight)
# ----------------------------------------------------------------------------
STORES = [
    ("S01", "London Oxford Street", "London", "United Kingdom", "UK", 3.0),
    ("S02", "London Stratford", "London", "United Kingdom", "UK", 2.0),
    ("S03", "Manchester Arndale", "Manchester", "United Kingdom", "UK", 2.5),
    ("S04", "Birmingham Bullring", "Birmingham", "United Kingdom", "UK", 2.5),
    ("S05", "Glasgow Argyle Street", "Glasgow", "United Kingdom", "UK", 1.5),
    ("S06", "Leeds Briggate", "Leeds", "United Kingdom", "UK", 1.5),
    ("S07", "Liverpool Church Street", "Liverpool", "United Kingdom", "UK", 1.5),
    ("S08", "Bristol Cabot Circus", "Bristol", "United Kingdom", "UK", 1.5),
    ("S09", "Edinburgh Princes Street", "Edinburgh", "United Kingdom", "UK", 1.2),
    ("S10", "Cardiff Queen Street", "Cardiff", "United Kingdom", "UK", 1.2),
    ("S11", "Newcastle Eldon Square", "Newcastle", "United Kingdom", "UK", 1.2),
    ("S12", "Nottingham Victoria Centre", "Nottingham", "United Kingdom", "UK", 1.2),
    ("S13", "Sheffield Meadowhall", "Sheffield", "United Kingdom", "UK", 1.2),
    ("S14", "Belfast Donegall Place", "Belfast", "United Kingdom", "UK", 1.2),
    ("S15", "Southampton Westquay", "Southampton", "United Kingdom", "UK", 1.0),
    ("S16", "Leicester Highcross", "Leicester", "United Kingdom", "UK", 1.0),
    ("S17", "Dublin Mary Street", "Dublin", "Ireland", "Ireland", 4.0),
    ("S18", "Dublin Dundrum", "Dublin", "Ireland", "Ireland", 2.0),
    ("S19", "Cork Patrick Street", "Cork", "Ireland", "Ireland", 2.0),
    ("S20", "Galway Shop Street", "Galway", "Ireland", "Ireland", 1.0),
    ("S21", "Limerick Crescent", "Limerick", "Ireland", "Ireland", 1.0),
    ("S22", "Madrid Gran Via", "Madrid", "Spain", "Europe", 2.0),
    ("S23", "Barcelona Portal de l'Angel", "Barcelona", "Spain", "Europe", 1.5),
    ("S24", "Paris Rivoli", "Paris", "France", "Europe", 1.5),
    ("S25", "Berlin Alexanderplatz", "Berlin", "Germany", "Europe", 1.5),
    ("S26", "Amsterdam Kalverstraat", "Amsterdam", "Netherlands", "Europe", 1.0),
    ("S27", "Rome Via del Corso", "Rome", "Italy", "Europe", 1.0),
    ("S28", "Lisbon Baixa", "Lisbon", "Portugal", "Europe", 1.0),
]
# Where customers live: share of customers by region
REGION_WEIGHTS = {"UK": 0.72, "Ireland": 0.14, "Europe": 0.14}
HOME_STORE_SHARE = 0.85    # share of visits made to the customer's home store
