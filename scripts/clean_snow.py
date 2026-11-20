"""Downloads the SLF daily snow data and writes it cleaned as Parquet."""

from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent
URL = "https://measurement-data.slf.ch/imis/data/daily_snow_values/daily_snow.csv"
RAW = BASE / "data_raw" / "daily_snow.csv"
TARGET = BASE / "data_clean" / "daily_snow.parquet"

RAW.parent.mkdir(parents=True, exist_ok=True)
TARGET.parent.mkdir(parents=True, exist_ok=True)

print("Downloading ...")
response = requests.get(URL, timeout=600)
response.raise_for_status()
RAW.write_bytes(response.content)
print(f"  {len(response.content) / 1e6:.1f} MB")

data = pd.read_csv(RAW, parse_dates=["measure_date"])
print(f"  {len(data)} rows read")

data["date"] = data["measure_date"].dt.tz_localize(None).dt.normalize()
data = data.drop(columns=["measure_date"])

negative = (data["HS"] < 0).sum()
data.loc[data["HS"] < 0, "HS"] = 0.0
print(f"  {negative} negative snow depths set to 0")

data = data[["station_code", "date", "hyear", "HS", "HN_1D"]]
data["station_code"] = data["station_code"].astype("category")
data["hyear"] = data["hyear"].astype("int16")
data["HS"] = data["HS"].astype("float32")
data["HN_1D"] = data["HN_1D"].astype("float32")

print(f"  memory: {data.memory_usage(deep=True).sum() / 1e6:.1f} MB")

data.to_parquet(TARGET, index=False)
print(f"\nWritten: {len(data)} rows up to {data['date'].max().date()}")
