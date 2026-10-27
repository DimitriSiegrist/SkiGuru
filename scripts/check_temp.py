"""Quick sanity check of the aggregated temperature data."""

from pathlib import Path

import pandas as pd

BASIS = Path(__file__).resolve().parent.parent
temp = pd.read_parquet(BASIS / "data_clean" / "daily_temp.parquet")
schnee = pd.read_parquet(BASIS / "data_clean" / "daily_snow.parquet")
temp["station_code"] = temp["station_code"].astype(str)
schnee["station_code"] = schnee["station_code"].astype(str)

print(f"{len(temp)} rows, {temp['station_code'].nunique()} stations")
print(f"{temp['datum'].min().date()} to {temp['datum'].max().date()}\n")

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

zusammen = schnee.merge(temp, on=["station_code", "datum"], how="inner")
print(f"Snow rows        : {len(schnee)}")
print(f"Temperature rows : {len(temp)}")
print(f"Matched on both  : {len(zusammen)}")
print(f"Snow without temperature: {len(schnee) - len(zusammen)}")