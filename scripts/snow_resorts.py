"""Match each resort to its nearest snow station and compute expected snow per day
(fallback until Dimi's snow forecast exists: historical values for each calendar day).

Writes data_clean/resort_stations.csv and data_clean/snow_expected.csv
Run from the repo root:  python scripts/snow_resort.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESORTS = ROOT / "data_clean" / "resorts.csv"
STATIONS = ROOT / "data_clean" / "stationen.csv"
SNOW = ROOT / "data_clean" / "daily_snow.parquet"
OUT_STATIONS = ROOT / "data_clean" / "resort_stations.csv"
OUT_SNOW = ROOT / "data_clean" / "snow_expected.csv"

SEASON = pd.date_range("2026-12-01", "2027-04-30", freq="D")
HS_CAP = 150      # cm snow depth → score 1
HN_CAP = 30       # cm new snow in 3 days → score 1
HN_MAX_DAY = 100  # cm new snow in one day above this = measurement error


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def nearest_station(resort, stations):
    d = haversine_km(resort["lat"], resort["lon"], stations["lat"], stations["lon"])
    best = stations.assign(dist_km=d).sort_values("dist_km").iloc[0]
    return best["station_code"], best["name"], best["hoehe"], round(best["dist_km"], 1)


def climatology(snow_station):
    """Per calendar day: median snow depth and mean new snow over 3 days."""
    s = snow_station.copy()
    s["day"] = s["datum"].dt.strftime("%m-%d")
    s["HN_clean"] = s["HN_1D"].where(s["HN_1D"] <= HN_MAX_DAY)

    hs = s.groupby("day")["HS"].median()
    hn = s.groupby("day")["HN_clean"].mean()
    ext = pd.concat([hn.iloc[-7:], hn, hn.iloc[:7]])          # wrap around New Year
    hn3 = 3 * ext.rolling(15, center=True).mean().iloc[7:-7]  # smooth ±7 days
    return pd.DataFrame({"HS_exp": hs, "HN3_exp": hn3})


def main():
    resorts = pd.read_csv(RESORTS)
    stations = pd.read_csv(STATIONS)
    stations = stations[stations["typ"] == "schnee"]
    snow = pd.read_parquet(SNOW)
    snow["station_code"] = snow["station_code"].astype(str)
    snow["datum"] = pd.to_datetime(snow["datum"])

    match_rows, snow_rows = [], []
    for _, r in resorts.iterrows():
        code, name, alt, dist = nearest_station(r, stations)
        match_rows.append({"resort": r["resort"], "station_code": code, "station_name": name,
                           "station_alt": alt, "dist_km": dist})

        clim = climatology(snow[snow["station_code"] == code])
        days = SEASON.strftime("%m-%d")
        exp = clim.reindex(days)
        snow_rows.append(pd.DataFrame({
            "resort": r["resort"],
            "station_code": code,
            "date": SEASON.date,
            "HS_exp": exp["HS_exp"].values,
            "HN3_exp": exp["HN3_exp"].round(1).values,
            "x_snow_depth": np.minimum(exp["HS_exp"].values / HS_CAP, 1).round(2),
            "x_new_snow": np.minimum(exp["HN3_exp"].values / HN_CAP, 1).round(2),
            "source": "historical median/mean (fallback)",
        }))

    pd.DataFrame(match_rows).to_csv(OUT_STATIONS, index=False)
    out = pd.concat(snow_rows, ignore_index=True)
    out.to_csv(OUT_SNOW, index=False)
    print(pd.DataFrame(match_rows))
    print(out.iloc[[0, 24, 45, 76, 104, 135]])
    print(f"Saved {len(out)} rows to {OUT_SNOW}")


if __name__ == "__main__":
    main()