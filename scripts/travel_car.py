"""Car distance and driving time (OpenRouteService) from Zurich HB to each resort,
plus car cost → data_clean/travel_car.csv

Needs ORS_KEY in .env (repo root) or as an environment variable.
Run from the repo root:  python scripts/travel_car.py
"""
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RESORTS = ROOT / "docs" / "resort_attributes.csv"
PARKING = ROOT / "docs" / "car_parking.csv"
OUT = ROOT / "data_clean" / "travel_car.csv"

ORS_URL = "https://api.heigit.org/openrouteservice/v2/directions/driving-car"
START = "Zürich HB"
START_COORDS = [8.5403, 47.3779]          # [lon, lat]
COST_PER_KM = 4135 / 15000                # TCS 2026 variable costs ≈ 0.28 CHF/km


def get_key():
    """ORS key from the environment, else from .env (never printed)."""
    if "ORS_KEY" in os.environ:
        return os.environ["ORS_KEY"]
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("ORS_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("ORS_KEY not found in environment or .env")


def drive(start, end, key):
    """One-way car route → (km, minutes)."""
    r = requests.post(ORS_URL,
                      headers={"Authorization": key, "Content-Type": "application/json"},
                      json={"coordinates": [start, end]},
                      timeout=30)
    r.raise_for_status()
    s = r.json()["routes"][0]["summary"]
    return s["distance"] / 1000, s["duration"] / 60


def main():
    key = get_key()
    resorts = pd.read_csv(RESORTS)
    parking = pd.read_csv(PARKING).set_index("resort")["parking_chf_day"]

    rows = []
    for _, r in resorts.iterrows():
        dest = [r["lon"], r["lat"]]
        km_out, min_out = drive(START_COORDS, dest, key)
        time.sleep(2)
        km_back, min_back = drive(dest, START_COORDS, key)
        time.sleep(2)
        park = parking.get(r["resort"], 0.0)
        km_round = km_out + km_back
        rows.append({
            "resort": r["resort"],
            "start": START,
            "km_out": round(km_out, 1),
            "km_back": round(km_back, 1),
            "km_round": round(km_round, 1),
            "t_out_min": round(min_out),
            "t_back_min": round(min_back),
            "t_round_min": round(min_out + min_back),
            "cost_per_km": round(COST_PER_KM, 4),
            "parking_chf_day": park,
            "k_car": round(COST_PER_KM * km_round + park, 2),
            "queried_on": date.today(),
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(out.T)
    print(f"Saved {len(out)} rows to {OUT}")


if __name__ == "__main__":
    main()