"""The snow melt model: how the snow depth develops over days without new snow."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
COEFFICIENTS = BASE / "data_clean" / "melt_model.json"

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


def load_coefficients():
    """The coefficients estimated by scripts/melt_model.py."""
    return json.loads(COEFFICIENTS.read_text())


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