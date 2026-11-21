"""Builds the table of days used to fit the snow melt model."""

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
SNOW = BASE / "data_clean" / "daily_snow.parquet"
TEMPERATURE = BASE / "data_clean" / "daily_temp.parquet"
TEMPERATURE_RECENT = BASE / "data_clean" / "daily_temp_recent.parquet"

MIN_DEPTH = 20     # cm of snow the day before
MIN_READINGS = 44  # of 48 half-hourly temperature values
MAX_CHANGE = 30    # cm per day, anything beyond is a measuring error
KEEP = 0.7         # share of the fresh snow stock that is left a day later
LATITUDE = 46.8    # degrees north, the middle of Switzerland


def sun_index(dates):
    """Possible solar energy per day, scaled to 1 at midsummer (FAO-56, equations 21 to 25)."""
    lat = np.deg2rad(LATITUDE)

    def energy(day):
        tilt = 0.409 * np.sin(2 * np.pi * day / 365 - 1.39)
        distance = 1 + 0.033 * np.cos(2 * np.pi * day / 365)
        sunset = np.arccos(-np.tan(lat) * np.tan(tilt))
        return (24 * 60 / np.pi) * 0.0820 * distance * (
            sunset * np.sin(lat) * np.sin(tilt) + np.cos(lat) * np.cos(tilt) * np.sin(sunset)
        )

    return energy(dates.dt.dayofyear) / energy(np.arange(1, 366)).max()


def load_temperature():
    """Archive plus the days added since by scripts/update_temperature.py."""
    temp = pd.read_parquet(TEMPERATURE)
    if TEMPERATURE_RECENT.exists():
        temp = pd.concat([temp, pd.read_parquet(TEMPERATURE_RECENT)], ignore_index=True)
    temp["station_code"] = temp["station_code"].astype(str)
    return temp.drop_duplicates(["station_code", "date"], keep="last")


def full_calendar(snow):
    """One row per station and calendar day, so that one row back is exactly one day back."""
    parts = []
    for code, group in snow.groupby("station_code"):
        dates = pd.date_range(group["date"].min(), group["date"].max(), freq="D")
        parts.append(pd.DataFrame({"station_code": code, "date": dates}))
    return pd.concat(parts, ignore_index=True)


def training_days():
    """Days without new snow, with everything the model needs."""
    snow = pd.read_parquet(SNOW)
    snow["station_code"] = snow["station_code"].astype(str)
    temp = load_temperature()

    days = full_calendar(snow)
    days = days.merge(snow[["station_code", "date", "HS", "HN_1D"]], on=["station_code", "date"], how="left")
    days = days.merge(temp[["station_code", "date", "TA_mean", "n"]], on=["station_code", "date"], how="left")
    days = days.sort_values(["station_code", "date"]).reset_index(drop=True)
    days["hyear"] = days["date"].dt.year + (days["date"].dt.month >= 10).astype(int)

    station = days["station_code"]
    days["HS_before"] = days.groupby(station)["HS"].shift(1)
    days["HN_before"] = days.groupby(station)["HN_1D"].shift(1)
    days["decline"] = days["HS_before"] - days["HS"]

    # Fresh snow stock: today's new snow counts fully, yesterday's 70 %, the day before 49 % ...
    new_snow = days["HN_1D"].fillna(0)
    stock = 0
    for k in range(21):
        stock = stock + KEEP**k * new_snow.groupby(station).shift(k).fillna(0)
    days["fresh"] = stock.groupby(station).shift(1)  # the model uses yesterday's stock

    # The stock is only reliable if new snow was reported on each of the last 11 days
    reported = days["HN_1D"].notna().astype(int)
    snow_known = reported.groupby(station).rolling(11).sum().reset_index(level=0, drop=True) == 11

    days["warmth"] = days["TA_mean"].clip(lower=0)
    days["sun"] = sun_index(days["date"])
    days["warm_sun"] = days["warmth"] * days["sun"]

    keep = (
        days["decline"].notna()
        & days["TA_mean"].notna()
        & (days["n"] >= MIN_READINGS)
        & (days["HS_before"] >= MIN_DEPTH)
        & (days["HN_1D"] == 0)       # no new snow on the day itself
        & (days["HN_before"] == 0)   # and none the day before
        & snow_known
        & (days["decline"].abs() <= MAX_CHANGE)
    )
    columns = ["station_code", "date", "hyear", "HS_before", "decline", "fresh", "warmth", "sun", "warm_sun"]
    return days.loc[keep, columns].reset_index(drop=True)


if __name__ == "__main__":
    days = training_days()
    print(f"{len(days):,} days from {days['station_code'].nunique()} stations, "
          f"{days['date'].min():%d.%m.%Y} to {days['date'].max():%d.%m.%Y}")
    print(f"{(days['hyear'] <= 2019).sum():,} of them up to winter 2019\n")

    print("Sun index:", sun_index(pd.Series(pd.to_datetime(["2025-12-21", "2026-03-21", "2026-06-21"]))).round(2).tolist())

    # Does one degree melt more in spring than in winter?
    days["season"] = days["date"].dt.month.map(
        {12: "Dec-Feb", 1: "Dec-Feb", 2: "Dec-Feb", 4: "Apr-Jun", 5: "Apr-Jun", 6: "Apr-Jun"}
    )
    days["temperature"] = pd.cut(days["warmth"], [-1, 0, 3, 6, 30], labels=["frost", "0 to 3", "3 to 6", "above 6"])
    table = days.pivot_table(index="temperature", columns="season", values="decline", aggfunc="mean", observed=True)
    print("\nMean decline in cm per day:")
    print(table[["Dec-Feb", "Apr-Jun"]].round(1))