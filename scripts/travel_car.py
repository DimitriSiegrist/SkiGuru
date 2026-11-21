"""Car distance and driving time (OpenRouteService) from Zurich HB to each resort,
plus car cost → data_clean/travel_car.csv

Needs ORS_KEY in .env (repo root) or as an environment variable.
Run from the repo root:  python scripts/travel_car.py
"""
import math
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RESORTS = ROOT / "data_clean" / "resorts.csv"
PARKING = ROOT / "docs" / "car_parking.csv"
OUT = ROOT / "data_clean" / "travel_car.csv"

ORS_URL = "https://api.heigit.org/openrouteservice/v2/directions/driving-car"
START = "Zürich HB"
START_COORDS = [8.5403, 47.3779]          # [lon, lat]
COST_PER_KM = 4135 / 15000                # TCS 2026 variable costs ≈ 0.28 CHF/km
DETOUR = 1.35                             # road km / straight-line km (Engelberg pilot: 85.5 / 63.4)
AVG_SPEED = 65                            # km/h, fallback only (Engelberg pilot: ≈ 67 km/h)

# Alpine passes closed in winter (≈ Nov–May): ORS must not route over them.
# Small boxes around the summits [lon, lat]; the Furka car train tunnel runs ~1.3 km south of the Furka box.
CLOSED_PASSES = {
    "Nufenen": (8.3875, 46.4775),
    "Grimsel": (8.3372, 46.5614),
    "Furka": (8.4147, 46.5728),
    "Susten": (8.4472, 46.7297),
}
BOX = 0.005                               # ≈ 550 m north–south, 380 m east–west

def box(lon, lat, d=BOX):
    """Closed square around one point, in ORS polygon format."""
    return [[[lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]]


AVOID = {"type": "MultiPolygon", "coordinates": [box(lon, lat) for lon, lat in CLOSED_PASSES.values()]}

def get_key():
    """ORS key from the environment, else from .env (never printed)."""
    if "ORS_KEY" in os.environ:
        return os.environ["ORS_KEY"]
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("ORS_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("ORS_KEY not found in environment or .env")


def crosses_closed_pass(coords):
    """True if any point of the route lies inside one of the closed-pass boxes."""
    for lon, lat in coords:
        for plon, plat in CLOSED_PASSES.values():
            if abs(lon - plon) <= BOX and abs(lat - plat) <= BOX:
                return True
    return False


def drive(start, end, key):
    """One-way car route → (km, minutes).
    Asks ORS normally first; only if that route crosses a winter-closed pass, asks again with the passes
    avoided (ORS accepts avoid areas only up to ~150 km straight-line distance)."""
    def request(avoid):
        body = {"coordinates": [start, end]}
        if avoid:
            body["options"] = {"avoid_polygons": AVOID}
        r = requests.post(ORS_URL + "/geojson",
                          headers={"Authorization": key, "Content-Type": "application/json"},
                          json=body, timeout=30)
        r.raise_for_status()
        return r.json()["features"][0]

    f = request(avoid=False)
    if crosses_closed_pass(f["geometry"]["coordinates"]):
        time.sleep(2)
        f = request(avoid=True)
    s = f["properties"]["summary"]
    return s["distance"] / 1000, s["duration"] / 60


def straight_line(start, end):
    """Fallback if ORS fails: straight-line distance × detour factor → (km, minutes)."""
    lon1, lat1 = map(math.radians, start)
    lon2, lat2 = map(math.radians, end)
    a = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    km = 2 * 6371 * math.asin(math.sqrt(a)) * DETOUR
    return km, km / AVG_SPEED * 60


def main():
    key = get_key()
    resorts = pd.read_csv(RESORTS)
    parking = (pd.read_csv(PARKING).set_index("resort_id")
               .reindex(resorts["resort_id"]))     # resort missing in the file → row of NaN

    rows = []
    failed = []
    for _, r in resorts.iterrows():
        p = parking.loc[r["resort_id"]]
        if pd.isna(p["parking_chf_day"]):
            print(f"NO PARKING {r['resort_id']}: assumed CHF 0")
        park = 0.0 if pd.isna(p["parking_chf_day"]) else p["parking_chf_day"]
        extra_chf = 0.0 if pd.isna(p["extra_chf_return"]) else p["extra_chf_return"]
        extra_min = 0 if pd.isna(p["extra_min_one_way"]) else int(p["extra_min_one_way"])
        
        train_mt = 0.0 if pd.isna(p["car_train_chf_mon_thu"]) else p["car_train_chf_mon_thu"]
        train_fs = 0.0 if pd.isna(p["car_train_chf_fri_sun"]) else p["car_train_chf_fri_sun"]        
        
        # drive to the valley station, unless the car must stop earlier (e.g. Zermatt → Täsch)
        dest = [r["lon"], r["lat"]] if pd.isna(p["park_lat"]) else [p["park_lon"], p["park_lat"]]

        try:
            km_out, min_out = drive(START_COORDS, dest, key)
            time.sleep(2)
            km_back, min_back = drive(dest, START_COORDS, key)
            time.sleep(2)
            method = "ors"
        except Exception as e:  # timeout, no road near the point, quota
            print(f"ORS FAILED {r['resort_id']}: {e} → straight-line fallback")
            failed.append(r["resort_id"])
            km_out, min_out = straight_line(START_COORDS, dest)
            km_back, min_back = km_out, min_out
            method = "fallback"

        km_round = km_out + km_back
        rows.append({
            "resort_id": r["resort_id"],
            "resort": r["resort"],
            "start": START,
            "method": method,
            "km_out": round(km_out, 1),
            "km_back": round(km_back, 1),
            "km_round": round(km_round, 1),
            "t_out_min": round(min_out),
            "t_back_min": round(min_back),
            "extra_min_one_way": extra_min,
            "t_round_min": round(min_out + min_back + 2 * extra_min),
            "cost_per_km": round(COST_PER_KM, 4),
            "parking_chf_day": park,
            "extra_chf_return": extra_chf,
            "car_train_chf_mon_thu": train_mt,    # return fare; chosen by date in src/finder.py
            "car_train_chf_fri_sun": train_fs,
            "k_car": round(COST_PER_KM * km_round + park + extra_chf, 2),   # without car train            "queried_on": date.today(),
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(out[["resort_id", "method", "km_round", "t_round_min", "k_car",
               "car_train_chf_mon_thu", "car_train_chf_fri_sun"]].to_string(index=False))
    print(f"Saved {len(out)} rows to {OUT}; ORS failed (fallback used): {failed or 'none'}")


if __name__ == "__main__":
    main()