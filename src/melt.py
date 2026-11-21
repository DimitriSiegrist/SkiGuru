"""The snow melt model: how the snow depth develops over days without new snow."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
MODEL = BASE / "data_clean" / "melt_model.json"

KEEP = 0.7       # share of the fresh snow stock that is left a day later
LATITUDE = 46.8  # degrees north, the middle of Switzerland


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

    day_of_year = pd.DatetimeIndex(dates).dayofyear.to_numpy()
    return energy(day_of_year) / energy(np.arange(1, 366)).max()


def load_model():
    """Coefficients and forecast errors as saved by scripts/melt_model.py."""
    return json.loads(MODEL.read_text())


def fresh_stock(history, day):
    """Fresh snow stock on `day`: the new snow of the past three weeks, older snowfalls count less.

    history: daily rows of one station with the columns date and HN_1D
    """
    age = (day - history["date"]).dt.days
    recent = (age >= 0) & (age <= 20)
    return float((KEEP ** age[recent] * history.loc[recent, "HN_1D"].fillna(0)).sum())


def forecast(depth, fresh, temperatures, first_day, coefficients):
    """Snow depth at the end of each coming day, assuming that no new snow falls.

    depth: snow depth today in cm
    fresh: fresh snow stock today in cm
    temperatures: mean air temperature of each coming day in degrees Celsius
    first_day: date of the first forecast day
    """
    dates = pd.date_range(first_day, periods=len(temperatures), freq="D")
    depths = []
    for temperature, sun in zip(temperatures, sun_index(dates)):
        decline = (
            coefficients["HS_before"] * depth
            + coefficients["fresh"] * fresh
            + coefficients["warm_sun"] * max(0.0, temperature) * sun
        )
        depth = max(0.0, depth - decline)
        fresh = fresh * KEEP
        depths.append(depth)
    return pd.Series(depths, index=dates)


def uncertainty(curve, errors):
    """Range in which the measured depth ended up in 95 of 100 forecasts over past dry spells.

    curve: forecast with today's depth in front
    errors: forecast minus measured after 7, 14 and 21 days, as 2.5 % and 97.5 % quantiles
    """
    day = np.arange(len(curve))
    horizons = [0] + [int(horizon) for horizon in errors]
    too_low = np.interp(day, horizons, [0] + [entry["low"] for entry in errors.values()])
    too_high = np.interp(day, horizons, [0] + [entry["high"] for entry in errors.values()])
    lower = (curve - too_high).clip(lower=0)
    upper = (curve - too_low).clip(upper=curve.iloc[0])  # without new snow the depth cannot rise
    return lower, upper