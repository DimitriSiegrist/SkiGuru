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
                   "snowmaking_share": 5, "x_snow_depth": 25, "x_new_snow": 10,
                   "rating_family": 5, "rating_freeride": 5, "rating_park": 5}


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
    car = data["car"][["resort_id", "t_round_min", "k_car",
                       "car_train_chf_mon_thu", "car_train_chf_fri_sun"]]
    static = (data["attrs"].drop(columns=["source_url", "collected_on"])
              .merge(train.rename(columns={"t_round_min": "t_train_min"}),
                     on="resort_id", validate="1:1")
              .merge(car.rename(columns={"t_round_min": "t_car_min"}),
                     on="resort_id", validate="1:1"))

    return static.merge(daily, on="resort_id", how="left", validate="1:m")


def scale(x, lo, hi):
    """Scale to 0–1 with a fixed range, clipped at 0 and 1; missing values → 0.5 (neutral)."""
    if pd.isna(x):
        return 0.5
    return min(max((x - lo) / (hi - lo), 0), 1)


def consumer_surplus(data, resort, date, B0=150, v=20, mode="train",
                     travel_pass="Halbtax", weights=None):
    """CS and its parts for one resort and date (date as 'YYYY-MM-DD')."""
    w = weights or DEFAULT_WEIGHTS
    a = data["attrs"].set_index("resort").loc[resort]

    x = {k: scale(a[k], *RANGES[k]) for k in RANGES}
    s = data["snow"].query("resort == @resort and date == @date").iloc[0]
    x["x_snow_depth"], x["x_new_snow"] = s["x_snow_depth"], s["x_new_snow"]

    B = B0 + sum(w[k] * x[k] for k in w)
    P = data["prices"].query("resort == @resort and date == @date")["price"].iloc[-1]

    if mode == "car":
        c = data["car"].set_index("resort").loc[resort]
        K, T = c["k_car"], c["t_round_min"] / 60
    else:
        t = data["train"].set_index("resort").loc[resort]
        K = {"none": t["fare_full_return"], "Halbtax": t["fare_halbtax_return"],
             "GA": 0.0}[travel_pass]
        T = t["t_round_min"] / 60

    return {"resort": resort, "date": date, "B": round(B, 2), "P": float(P),
            "K": float(K), "T_h": round(T, 2), "vT": round(v * T, 2),
            "CS": round(B - P - K - v * T, 2)}