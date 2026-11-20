"""Quick sanity check of the aggregated temperature data."""

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
temp = pd.read_parquet(BASE / "data_clean" / "daily_temp.parquet")
snow = pd.read_parquet(BASE / "data_clean" / "daily_snow.parquet")
temp["station_code"] = temp["station_code"].astype(str)
snow["station_code"] = snow["station_code"].astype(str)

print(f"{len(temp)} rows, {temp['station_code'].nunique()} stations")
print(f"{temp['date'].min().date()} to {temp['date'].max().date()}\n")

print("Completeness of the day (n = half-hourly values, 48 is full):")
print(f"  n == 48 : {(temp['n'] == 48).mean() * 100:5.1f} %")
print(f"  n >= 40 : {(temp['n'] >= 40).mean() * 100:5.1f} %")
print(f"  n <  24 : {(temp['n'] < 24).mean() * 100:5.1f} %\n")

print("Missing values in per cent:")
print((temp[["TA_mean", "TA_min", "TA_max", "TSS_mean", "RSWR_mean"]]
       .isna().mean() * 100).round(2).to_string())
print()

print("Air temperature, daily mean:")
print(temp["TA_mean"].describe().round(2).to_string())
print()

print(f"TA_mean below -35 C : {(temp['TA_mean'] < -35).sum()}")
print(f"TA_mean above  30 C : {(temp['TA_mean'] > 30).sum()}")
print(f"TSS_mean above   5 C: {(temp['TSS_mean'] > 5).sum()}\n")

merged = snow.merge(temp, on=["station_code", "date"], how="inner")
print(f"Snow rows        : {len(snow)}")
print(f"Temperature rows : {len(temp)}")
print(f"Matched on both  : {len(merged)}")
print(f"Snow without temperature: {len(snow) - len(merged)}")