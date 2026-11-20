"""Downloads the 30-minute IMIS station files and aggregates them to daily values."""

import time
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent
STATIONS = BASE / "data_clean" / "stations.csv"
CACHE = BASE / "data_raw" / "temp_daily"
TMP = BASE / "data_raw" / "_station.csv"
TARGET = BASE / "data_clean" / "daily_temp.parquet"
URL = "https://measurement-data.slf.ch/imis/data/by_station/{code}.csv"

VALUES = ["TA_30MIN_MEAN", "TSS_30MIN_MEAN", "RSWR_30MIN_MEAN"]
COLUMNS = {"measure_date", *VALUES}

CACHE.mkdir(parents=True, exist_ok=True)
TARGET.parent.mkdir(parents=True, exist_ok=True)


def download(code):
    """Downloads one station file to TMP. Returns False if the file does not exist."""
    with requests.get(URL.format(code=code), stream=True, timeout=600) as response:
        if response.status_code == 404:
            return False
        response.raise_for_status()
        with open(TMP, "wb") as file:
            for chunk in response.iter_content(1 << 20):
                file.write(chunk)
    return True


def aggregate(code):
    """Reads TMP and condenses the half-hourly values to daily values."""
    raw = pd.read_csv(TMP, usecols=lambda s: s in COLUMNS)

    for column in VALUES:
        if column not in raw.columns:
            raw[column] = pd.NA

    timestamp = pd.to_datetime(raw["measure_date"], utc=True, format="ISO8601")
    # Day t covers the 24 hours up to 06:00 UTC on day t, as in the SLF daily data
    raw["date"] = (
        (timestamp - pd.Timedelta(hours=6)).dt.tz_localize(None).dt.normalize()
        + pd.Timedelta(days=1)
    )

    days = (
        raw.groupby("date")
        .agg(
            TA_mean=("TA_30MIN_MEAN", "mean"),
            TA_min=("TA_30MIN_MEAN", "min"),
            TA_max=("TA_30MIN_MEAN", "max"),
            TSS_mean=("TSS_30MIN_MEAN", "mean"),
            TSS_max=("TSS_30MIN_MEAN", "max"),
            RSWR_mean=("RSWR_30MIN_MEAN", "mean"),
            n=("TA_30MIN_MEAN", "count"),
        )
        .reset_index()
    )

    days.insert(0, "station_code", code)
    for column in days.columns:
        if column.startswith(("TA_", "TSS_", "RSWR_")):
            days[column] = days[column].astype("float32")
    days["n"] = days["n"].astype("int16")
    return days


codes = pd.read_csv(STATIONS)
codes = sorted(codes.loc[codes["type"] == "snow", "station_code"])

print(f"{len(codes)} snow stations\n")
start = time.time()
missing = []

for i, code in enumerate(codes, 1):
    cached = CACHE / f"{code}.parquet"
    if cached.exists():
        print(f"[{i:3}/{len(codes)}] {code}  already done")
        continue

    if not download(code):
        print(f"[{i:3}/{len(codes)}] {code}  no file on the server")
        missing.append(code)
        continue

    mb = TMP.stat().st_size / 1e6
    days = aggregate(code)
    days.to_parquet(cached, index=False)
    TMP.unlink()

    print(f"[{i:3}/{len(codes)}] {code}  {mb:5.1f} MB  ->  {len(days)} days")

print(f"\nDownload and aggregation took {(time.time() - start) / 60:.1f} minutes")

# Cache files written before the columns were renamed still call the date "datum"
combined = pd.concat(
    [
        pd.read_parquet(p).rename(columns={"datum": "date"})
        for p in sorted(CACHE.glob("*.parquet"))
    ],
    ignore_index=True,
)
combined["station_code"] = combined["station_code"].astype("category")
combined.to_parquet(TARGET, index=False)

print(f"\n{len(combined)} rows for {combined['station_code'].nunique()} stations")
print(f"{combined['date'].min().date()} to {combined['date'].max().date()}")
print(f"File: {TARGET.stat().st_size / 1e6:.1f} MB")
if missing:
    print(f"\nNo data file: {missing}")
