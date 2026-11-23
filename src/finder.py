"""Consumer surplus for the resort finder: CS = B − P − K − v·T, with B = B0 + Σ w_k · x̃_k."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# fixed reference ranges = real min/max of the 25 resorts, rounded outward (task 10.3)
# set once, not min-max across the list → B does not change when a resort is added
RANGES = {"piste_km": (25, 425), "lifts": (5, 70), "vertical_drop": (600, 2400),
          "top_alt": (1800, 3900), "snowmaking_share": (0, 1),
          "rating_family": (1, 5), "rating_freeride": (1, 5), "rating_park": (1, 5)}  # Skiresort stars

# default weights: CHF for the best vs. the worst value of each attribute
DEFAULT_WEIGHTS = {"piste_km": 30, "lifts": 5, "vertical_drop": 15, "top_alt": 10,
                   "snowmaking_share": 5, "difficulty": 10, "x_snow_depth": 25, "x_new_snow": 10,
                   "rating_family": 5, "rating_freeride": 5, "rating_park": 5}

# difficulty mix: which piste colour counts for the user's level (task 9)
LEVEL_KM = {"beginner": "km_blue", "intermediate": "km_red", "expert": "km_black"}

# fixed ranges for the share of piste km per colour = real min/max rounded outward (task 15.2)
LEVEL_RANGES = {"beginner": (0.05, 0.65), "intermediate": (0.20, 0.80), "expert": (0.00, 0.40)}

# public holidays on Mon–Thu in the season → car-train weekend fare (25 Dec and 1 Jan 2027 are Fridays)
HOLIDAYS = ["2027-03-29"]   # Easter Monday
# travel pass discount on the Zermatt shuttle (MGB: free with GA, half price with Halbtax)
PASS_DISCOUNT = {"none": 0.0, "Halbtax": 0.5, "GA": 1.0}


def load_data():
    """All inputs as DataFrames (attributes, prices, snow, train, car)."""
    return {
        "attrs": pd.read_csv(ROOT / "data_clean" / "resorts.csv"),
        "prices": pd.read_csv(ROOT / "data_clean" / "prices.csv"),
        "snow": pd.read_csv(ROOT / "data_clean" / "snow_expected.csv"),
        "train": pd.read_csv(ROOT / "data_clean" / "travel_train.csv"),
        "car": pd.read_csv(ROOT / "data_clean" / "travel_car.csv"),
    }


def merge_tables(data):
    """One row per resort and date: attributes, train, car (per resort) + snow, price (per day)."""
    # prices: the scraper appends every week → keep the latest scrape per resort and date
    prices = (data["prices"].sort_values("scraped_on")
              .drop_duplicates(["resort_id", "date"], keep="last")
              [["resort_id", "date", "price", "source", "scraped_on"]]
              .rename(columns={"source": "price_source"}))
    snow = data["snow"][["resort_id", "date", "station_code", "HS_exp", "HN3_exp",
                         "x_snow_depth", "x_new_snow"]]
    # snow covers all 151 days (1 Dec–30 Apr); days without a price (resort closed) keep price = NaN
    daily = snow.merge(prices, on=["resort_id", "date"], how="left", validate="1:1")

    train = data["train"][["resort_id", "t_round_min", "fare_full_return", "fare_halbtax_return"]]
    car = data["car"][["resort_id", "t_round_min", "k_car", "extra_chf_return",
                       "car_train_chf_mon_thu", "car_train_chf_fri_sun"]]
    static = (data["attrs"].drop(columns=["source_url", "collected_on"])
              .merge(train.rename(columns={"t_round_min": "t_train_min"}),
                     on="resort_id", validate="1:1")
              .merge(car.rename(columns={"t_round_min": "t_car_min"}),
                     on="resort_id", validate="1:1"))

    return static.merge(daily, on="resort_id", how="left", validate="1:m")


def scaled_attributes(df, level="intermediate"):
    """x̃ (0–1) per attribute and row: fixed ranges (RANGES), snow already scaled in
    snow_expected.csv, difficulty = share of piste km at the user's level."""
    x = pd.DataFrame({k: scale(df[k], *RANGES[k]) for k in RANGES}, index=df.index)
    x["difficulty"] = scale(df[LEVEL_KM[level]] / df["piste_km"], *LEVEL_RANGES[level])
    x["x_snow_depth"] = df["x_snow_depth"]
    x["x_new_snow"] = df["x_new_snow"]
    return x


def scale(x, lo, hi):
    """Scale to 0–1 with a fixed range, clipped at 0 and 1; missing values → 0.5 (neutral).
    Works for a single value and for a whole column (pd.Series)."""
    s = ((pd.Series(x, dtype=float) - lo) / (hi - lo)).clip(0, 1).fillna(0.5)
    return s if isinstance(x, pd.Series) else float(s.iloc[0])


def benefit(x, weights=None, B0=150):
    """B = B0 + Σ w_k · x̃_k per row. Also returns the contributions w_k · x̃_k (CHF),
    one column per attribute, for the breakdown on page 3 (task 17.3)."""
    w = pd.Series(weights or DEFAULT_WEIGHTS)
    contrib = x[w.index] * w          # each column x̃_k times its weight w_k
    return B0 + contrib.sum(axis=1), contrib


def travel_cost(df, mode="train", travel_pass="Halbtax"):
    """K (CHF, return) and T (hours, round trip incl. walk / shuttle) per row."""
    if mode == "car":
        # car train (Lötschberg, Furka): weekend fare on Fri–Sun and Mon–Thu holidays (BLS)
        weekend = (pd.to_datetime(df["date"]).dt.dayofweek >= 4) | df["date"].isin(HOLIDAYS)
        car_train = df["car_train_chf_fri_sun"].where(weekend, df["car_train_chf_mon_thu"])
        # k_car contains the full shuttle fare (Zermatt) → travel pass discount only on the shuttle,
        # not on the car train (GA / Halbtax not valid there)
        K = df["k_car"] - PASS_DISCOUNT[travel_pass] * df["extra_chf_return"] + car_train
        T = df["t_car_min"] / 60
    else:
        K = {"none": df["fare_full_return"], "Halbtax": df["fare_halbtax_return"],
             "GA": pd.Series(0.0, index=df.index)}[travel_pass]
        T = df["t_train_min"] / 60
    return K, T


def consumer_surplus(df, date, B0=150, v=20, mode="train", travel_pass="Halbtax",
                     level="intermediate", weights=None):
    """CS = B − P − K − v·T for all resorts on one date (date as 'YYYY-MM-DD').
    df = merge_tables(load_data()). Resorts without a price on that date get CS = NaN."""
    d = df[df["date"] == date]
    B, _ = benefit(scaled_attributes(d, level), weights, B0)
    K, T = travel_cost(d, mode, travel_pass)
    return pd.DataFrame({
        "resort_id": d["resort_id"], "resort": d["resort"], "date": d["date"],
        "B": B.round(2), "P": d["price"], "K": K.round(2), "T_h": T.round(2),
        "vT": (v * T).round(2), "CS": (B - d["price"] - K - v * T).round(2),
    }).reset_index(drop=True)