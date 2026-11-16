"""Consumer surplus for the resort finder: CS = B − P − K − v·T, with B = B0 + Σ w_k · x̃_k."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# fixed reference ranges for the pilot (later: min-max across all resorts, task 15)
RANGES = {"piste_km": (0, 300), "lifts": (0, 80), "vertical_drop": (0, 2200),
          "top_alt": (1500, 3500), "snowmaking_share": (0, 1),
          "family_friendly": (0, 1), "freeride": (0, 1), "parks": (0, 1)}

# default weights: CHF for the best vs. the worst value of each attribute
DEFAULT_WEIGHTS = {"piste_km": 30, "lifts": 5, "vertical_drop": 15, "top_alt": 10,
                   "snowmaking_share": 5, "x_snow_depth": 25, "x_new_snow": 10,
                   "family_friendly": 5, "freeride": 5, "parks": 5}


def load_data():
    """All inputs as DataFrames (attributes, prices, snow, train, car)."""
    return {
        "attrs": pd.read_csv(ROOT / "docs" / "resort_attributes.csv"),
        "prices": pd.read_csv(ROOT / "data_clean" / "prices.csv"),
        "snow": pd.read_csv(ROOT / "data_clean" / "snow_expected.csv"),
        "train": pd.read_csv(ROOT / "data_clean" / "travel_train.csv"),
        "car": pd.read_csv(ROOT / "data_clean" / "travel_car.csv"),
    }


def scale(x, lo, hi):
    """Scale to 0–1 with a fixed range, clipped at 0 and 1."""
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