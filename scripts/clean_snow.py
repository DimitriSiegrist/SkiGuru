"""Downloads the SLF daily snow data and writes it cleaned as Parquet."""

from pathlib import Path

import pandas as pd
import requests

BASIS = Path(__file__).resolve().parent.parent
URL = "https://measurement-data.slf.ch/imis/data/daily_snow_values/daily_snow.csv"
ROH = BASIS / "data_raw" / "daily_snow.csv"
ZIEL = BASIS / "data_clean" / "daily_snow.parquet"

ROH.parent.mkdir(parents=True, exist_ok=True)
ZIEL.parent.mkdir(parents=True, exist_ok=True)

print("Downloading ...")
antwort = requests.get(URL, timeout=600)
antwort.raise_for_status()
ROH.write_bytes(antwort.content)
print(f"  {len(antwort.content) / 1e6:.1f} MB")

daten = pd.read_csv(ROH, parse_dates=["measure_date"])
print(f"  {len(daten)} rows read")

daten["datum"] = daten["measure_date"].dt.tz_localize(None).dt.normalize()
daten = daten.drop(columns=["measure_date"])

negativ = (daten["HS"] < 0).sum()
daten.loc[daten["HS"] < 0, "HS"] = 0.0
print(f"  {negativ} negative snow depths set to 0")

daten = daten[["station_code", "datum", "hyear", "HS", "HN_1D"]]
daten["station_code"] = daten["station_code"].astype("category")
daten["hyear"] = daten["hyear"].astype("int16")
daten["HS"] = daten["HS"].astype("float32")
daten["HN_1D"] = daten["HN_1D"].astype("float32")

print(f"  memory: {daten.memory_usage(deep=True).sum() / 1e6:.1f} MB")

daten.to_parquet(ZIEL, index=False)
print(f"\nWritten: {len(daten)} rows up to {daten['datum'].max().date()}")