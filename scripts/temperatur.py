"""Downloads the 30-minute IMIS station files and aggregates them to daily values."""

import time
from pathlib import Path

import pandas as pd
import requests

BASIS = Path(__file__).resolve().parent.parent
STATIONEN = BASIS / "data_clean" / "stationen.csv"
CACHE = BASIS / "data_raw" / "temp_daily"
TMP = BASIS / "data_raw" / "_station.csv"
ZIEL = BASIS / "data_clean" / "daily_temp.parquet"
URL = "https://measurement-data.slf.ch/imis/data/by_station/{code}.csv"

WERTE = ["TA_30MIN_MEAN", "TSS_30MIN_MEAN", "RSWR_30MIN_MEAN"]
SPALTEN = {"measure_date", *WERTE}

CACHE.mkdir(parents=True, exist_ok=True)
ZIEL.parent.mkdir(parents=True, exist_ok=True)


def herunterladen(code):
    """Laedt eine Stationsdatei nach TMP. Gibt False zurueck, wenn es sie nicht gibt."""
    with requests.get(URL.format(code=code), stream=True, timeout=600) as antwort:
        if antwort.status_code == 404:
            return False
        antwort.raise_for_status()
        with open(TMP, "wb") as datei:
            for stueck in antwort.iter_content(1 << 20):
                datei.write(stueck)
    return True


def aggregieren(code):
    """Liest TMP und verdichtet die Halbstundenwerte auf Tageswerte."""
    roh = pd.read_csv(TMP, usecols=lambda s: s in SPALTEN)

    for spalte in WERTE:
        if spalte not in roh.columns:
            roh[spalte] = pd.NA

    zeit = pd.to_datetime(roh["measure_date"], utc=True, format="ISO8601")
    # Tag t umfasst die 24 Stunden bis 06:00 UTC an Tag t, wie bei den SLF-Tagesdaten
    roh["datum"] = (
        (zeit - pd.Timedelta(hours=6)).dt.tz_localize(None).dt.normalize()
        + pd.Timedelta(days=1)
    )

    tage = (
        roh.groupby("datum")
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

    tage.insert(0, "station_code", code)
    for spalte in tage.columns:
        if spalte.startswith(("TA_", "TSS_", "RSWR_")):
            tage[spalte] = tage[spalte].astype("float32")
    tage["n"] = tage["n"].astype("int16")
    return tage


codes = pd.read_csv(STATIONEN)
codes = sorted(codes.loc[codes["typ"] == "schnee", "station_code"])

print(f"{len(codes)} snow stations\n")
start = time.time()
fehlend = []

for i, code in enumerate(codes, 1):
    ziel = CACHE / f"{code}.parquet"
    if ziel.exists():
        print(f"[{i:3}/{len(codes)}] {code}  already done")
        continue

    if not herunterladen(code):
        print(f"[{i:3}/{len(codes)}] {code}  no file on the server")
        fehlend.append(code)
        continue

    mb = TMP.stat().st_size / 1e6
    tage = aggregieren(code)
    tage.to_parquet(ziel, index=False)
    TMP.unlink()

    print(f"[{i:3}/{len(codes)}] {code}  {mb:5.1f} MB  ->  {len(tage)} days")

print(f"\nDownload and aggregation took {(time.time() - start) / 60:.1f} minutes")

alle = pd.concat(
    [pd.read_parquet(p) for p in sorted(CACHE.glob("*.parquet"))],
    ignore_index=True,
)
alle["station_code"] = alle["station_code"].astype("category")
alle.to_parquet(ZIEL, index=False)

print(f"\n{len(alle)} rows for {alle['station_code'].nunique()} stations")
print(f"{alle['datum'].min().date()} to {alle['datum'].max().date()}")
print(f"File: {ZIEL.stat().st_size / 1e6:.1f} MB")
if fehlend:
    print(f"\nNo data file: {fehlend}")