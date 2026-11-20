"""Keeps the temperature data current without rebuilding the archive.

Fetches the last 7 days of half-hourly measurements for every snow station from
the SLF API, aggregates them to daily values and adds them to
data_clean/daily_temp_recent.parquet. The large archive daily_temp.parquet is
not touched.
Run from the repo root:  python scripts/update_temperature.py
"""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from src.daily import to_daily  # noqa: E402

STATIONS = BASE / "data_clean" / "stations.csv"
ARCHIVE = BASE / "data_clean" / "daily_temp.parquet"
RECENT = BASE / "data_clean" / "daily_temp_recent.parquet"
API = "https://measurement-api.slf.ch/public/api/imis/station/{code}/measurements"
DAYS = 7  # the API allows 1, 3 or 7
KEY = ["station_code", "date"]


def fetch(code):
    """Half-hourly rows of one station. None if the API has nothing for it."""
    response = requests.get(API.format(code=code), params={"period_in_days": DAYS}, timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    rows = response.json()
    return pd.DataFrame(rows) if rows else None


def compare_with_archive(recent):
    """Prints how closely the API values match the archive on days both contain."""
    if not ARCHIVE.exists():
        return
    archive = pd.read_parquet(ARCHIVE)
    archive["station_code"] = archive["station_code"].astype(str)
    both = recent.merge(archive, on=KEY, suffixes=("", "_archive"))
    both = both[(both["n"] == 48) & (both["n_archive"] == 48)]
    if both.empty:
        print("No complete days in common with the archive yet")
        return
    gap = (both["TA_mean"] - both["TA_mean_archive"]).abs()
    print(f"Days in common with the archive: {len(both)}, "
          f"largest difference in TA_mean: {gap.max():.2f} °C")


def main():
    codes = pd.read_csv(STATIONS)
    codes = sorted(codes.loc[codes["type"] == "snow", "station_code"])
    print(f"{len(codes)} snow stations, last {DAYS} days\n")

    frames, empty, failed = [], [], []
    for code in codes:
        try:
            raw = fetch(code)
        except requests.RequestException as error:
            print(f"  {code}  failed: {error}")
            failed.append(code)
            continue
        if raw is None:
            empty.append(code)
            continue
        frames.append(to_daily(raw, code))
        time.sleep(0.2)  # be gentle with the API

    if not frames:
        sys.exit("No station could be fetched, nothing written")

    new = pd.concat(frames, ignore_index=True)

    if RECENT.exists():
        old = pd.read_parquet(RECENT)
        old["station_code"] = old["station_code"].astype(str)
        recent = pd.concat([old, new], ignore_index=True)
    else:
        recent = new

    # A day fetched again replaces the earlier version of itself
    recent = (
        recent.drop_duplicates(KEY, keep="last")
        .sort_values(KEY)
        .reset_index(drop=True)
    )
    compare_with_archive(recent)

    recent["station_code"] = recent["station_code"].astype("category")
    recent.to_parquet(RECENT, index=False)

    print(f"\nFetched {new['date'].nunique()} complete days for {len(frames)} stations, "
          f"{new['date'].min().date()} to {new['date'].max().date()}")
    print(f"Recent file: {len(recent)} rows, "
          f"{recent['date'].min().date()} to {recent['date'].max().date()}, "
          f"{RECENT.stat().st_size / 1e3:.0f} kB")
    if empty:
        print(f"No data from the API: {empty}")
    if failed:
        print(f"Failed: {failed}")


if __name__ == "__main__":
    main()