"""Hand-checkable test of src/finder.py (checklist task 15.4).

Three made-up resorts on Fri 15 Jan 2027, chosen so that every scaled value is easy:
A = top of every reference range (x̃ = 1), B = middle (x̃ = 0.5), C = bottom (x̃ = 0),
except C's park rating, which is missing → neutral 0.5.

Run from the repo root:  python -m pytest tests   (or: python tests/test_finder.py)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.finder import consumer_surplus, rank_resorts  # noqa: E402


def toy(date="2027-01-15"):
    """Same columns as merge_tables(), three resorts, one date."""
    return pd.DataFrame({
        "resort_id": ["a", "b", "c"], "resort": ["A", "B", "C"], "date": [date] * 3,
        # RANGES: piste km 25–425, lifts 5–70, vertical drop 600–2400 m, top 1800–3900 m
        "piste_km": [425, 225, 25], "lifts": [70, 37.5, 5],
        "vertical_drop": [2400, 1500, 600], "top_alt": [3900, 2850, 1800],
        "snowmaking_share": [1, 0.5, 0],
        "rating_family": [5, 3, 1], "rating_freeride": [5, 3, 1], "rating_park": [5, 3, None],
        # intermediate → red share, range 0.20–0.80: 340/425 = 0.8, 112.5/225 = 0.5, 5/25 = 0.2
        "km_red": [340, 112.5, 5],
        "x_snow_depth": [1, 0.5, 0], "x_new_snow": [1, 0.5, 0],
        "price": [90, 60, 40],
        "fare_full_return": [100, 60, 40], "fare_halbtax_return": [50, 30, 20],
        "t_train_min": [240, 180, 120],
        # A: car train (56 Mon–Thu / 62 Fri–Sun) and a shuttle of CHF 20 inside k_car
        "k_car": [70, 50, 30], "extra_chf_return": [20, 0, 0],
        "car_train_chf_mon_thu": [56, 0, 0], "car_train_chf_fri_sun": [62, 0, 0],
        "t_car_min": [180, 120, 90],
    })


def test_train():
    cs = consumer_surplus(toy(), "2027-01-15")   # train, Halbtax, B0 = 150, v = 20
    assert cs["B"].tolist() == [275, 212.5, 152.5]
    assert cs["K"].tolist() == [50, 30, 20]
    assert cs["vT"].tolist() == [80, 60, 40]
    assert cs["CS"].tolist() == [55, 62.5, 52.5]
    assert rank_resorts(cs)["resort"].tolist() == ["B", "A", "C"]


def test_car():
    cs = consumer_surplus(toy(), "2027-01-15", mode="car")   # Friday → weekend car-train fare
    assert cs["K"].tolist() == [122, 50, 30]
    assert cs["vT"].tolist() == [60, 40, 30]
    assert cs["CS"].tolist() == [3, 62.5, 52.5]
    # Thursday → weekday fare; Easter Monday → weekend fare; GA → shuttle free
    assert consumer_surplus(toy("2027-01-14"), "2027-01-14", mode="car")["K"][0] == 116
    assert consumer_surplus(toy("2027-03-29"), "2027-03-29", mode="car")["K"][0] == 122
    assert consumer_surplus(toy(), "2027-01-15", mode="car", travel_pass="GA")["K"][0] == 112


def test_budget_and_missing_price():
    cs = consumer_surplus(toy(), "2027-01-15")             # train: P + K = 140, 90, 60
    assert rank_resorts(cs, budget=100)["resort"].tolist() == ["B", "C"]
    assert rank_resorts(cs, budget=90)["resort"].tolist() == ["B", "C"]   # B exactly at the limit
    assert rank_resorts(cs, budget=50).empty
    no_price = toy()
    no_price.loc[0, "price"] = None                        # A closed on that day
    cs = consumer_surplus(no_price, "2027-01-15")
    assert rank_resorts(cs)["resort"].tolist() == ["B", "C"]


if __name__ == "__main__":       # without pytest: python tests/test_finder.py
    test_train()
    test_car()
    test_budget_and_missing_price()
    print("all tests passed")