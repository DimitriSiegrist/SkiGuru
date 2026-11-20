"""Loading the data for the app: snow, temperature, stations and avalanche bulletin."""

from pathlib import Path

import pandas as pd
import requests
import streamlit as st

BASE = Path(__file__).resolve().parent.parent
SNOW = BASE / "data_clean" / "daily_snow.parquet"
TEMPERATURE = BASE / "data_clean" / "daily_temp.parquet"
TEMPERATURE_RECENT = BASE / "data_clean" / "daily_temp_recent.parquet"
STATIONS = BASE / "data_clean" / "stations.csv"
API = "https://measurement-api.slf.ch/public/api/imis/daily-snow"
BULLETIN = "https://aws.slf.ch/api/bulletin/caaml/en/geojson"


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_api(days=7):
    """Fetches the last few days from the SLF API. Only 1, 3 or 7 are allowed."""
    response = requests.get(API, params={"period_in_days": days}, timeout=20)
    response.raise_for_status()

    new = pd.DataFrame(response.json())
    if new.empty:
        return None

    new["date"] = pd.to_datetime(new["measure_date"]).dt.normalize()
    new["hyear"] = new["date"].dt.year + (new["date"].dt.month >= 10).astype(int)
    new.loc[new["HS"] < 0, "HS"] = 0.0
    return new[["station_code", "date", "hyear", "HS", "HN_1D"]]


@st.cache_data(ttl=1800, show_spinner="Loading snow data ...")
def load_snow():
    """Returns (data, live). live is False if the API could not be reached."""
    data = pd.read_parquet(SNOW)
    data["station_code"] = data["station_code"].astype(str)

    try:
        new = _fetch_api()
    except Exception:
        new = None

    if new is None:
        return data.sort_values(["station_code", "date"]).reset_index(drop=True), False

    data = pd.concat([data, new], ignore_index=True)
    data = (
        data.drop_duplicates(["station_code", "date"], keep="last")
        .sort_values(["station_code", "date"])
        .reset_index(drop=True)
    )
    return data, True


@st.cache_data(ttl=1800, show_spinner=False)
def load_temperature():
    """Daily air and snow surface temperatures per station.

    The archive holds the long history. The recent file holds the days added
    since by scripts/update_temperature.py and wins where both have a day.
    """
    temp = pd.read_parquet(TEMPERATURE)
    temp["station_code"] = temp["station_code"].astype(str)

    if TEMPERATURE_RECENT.exists():
        recent = pd.read_parquet(TEMPERATURE_RECENT)
        recent["station_code"] = recent["station_code"].astype(str)
        temp = pd.concat([temp, recent], ignore_index=True)
        temp = (
            temp.drop_duplicates(["station_code", "date"], keep="last")
            .sort_values(["station_code", "date"])
            .reset_index(drop=True)
        )
    return temp


@st.cache_data(ttl=1800, show_spinner=False)
def load_bulletin():
    """Current SLF avalanche bulletin as GeoJSON. None if unavailable."""
    try:
        response = requests.get(BULLETIN, timeout=15)
        response.raise_for_status()
        content = response.json()
        if content.get("features"):
            return content
    except Exception:
        pass
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def load_stations(active_days=7):
    """Snow stations with coordinates and current snow depth."""
    data, _ = load_snow()

    stations = pd.read_csv(STATIONS)
    stations = stations[stations["type"] == "snow"].copy()

    last_seen = data.groupby("station_code")["date"].max()
    active = last_seen[last_seen >= last_seen.max() - pd.Timedelta(days=active_days)].index
    stations = stations[stations["station_code"].isin(active)]

    latest = (
        data[data["station_code"].isin(stations["station_code"])]
        .sort_values("date")
        .groupby("station_code")
        .last()
        .reset_index()[["station_code", "HS"]]
    )
    stations = stations.merge(latest, on="station_code", how="left")
    stations["HS"] = stations["HS"].fillna(0).round(0)
    return stations