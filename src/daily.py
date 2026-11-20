"""Turns half-hourly IMIS measurements into daily values."""

import pandas as pd

VALUES = ["TA_30MIN_MEAN", "TSS_30MIN_MEAN", "RSWR_30MIN_MEAN"]
COLUMNS = {"measure_date", *VALUES}

# Day t covers the 24 hours up to 06:00 UTC on day t, as in the SLF daily snow data
DAY_START = pd.Timedelta(hours=6)
STEP = pd.Timedelta(minutes=30)


def to_daily(raw, code, complete_only=True):
    """Condenses the half-hourly rows of one station to one row per day."""
    raw = raw.copy()
    for column in VALUES:
        if column not in raw.columns:
            raw[column] = pd.NA
        raw[column] = pd.to_numeric(raw[column], errors="coerce")

    timestamp = pd.to_datetime(raw["measure_date"], utc=True, format="ISO8601")
    timestamp = timestamp.dt.tz_localize(None)
    raw["date"] = (timestamp - DAY_START).dt.normalize() + pd.Timedelta(days=1)

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

    # Drop days that are cut off by the start or the end of the data
    if complete_only and not days.empty:
        first_slot = days["date"] - pd.Timedelta(days=1) + DAY_START
        last_slot = days["date"] + DAY_START - STEP
        inside = (first_slot >= timestamp.min()) & (last_slot <= timestamp.max())
        days = days[inside].reset_index(drop=True)

    days.insert(0, "station_code", code)
    for column in days.columns:
        if column.startswith(("TA_", "TSS_", "RSWR_")):
            days[column] = days[column].astype("float32")
    days["n"] = days["n"].astype("int16")
    return days