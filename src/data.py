"""Loading the snow data: Parquet base plus the last few days from the SLF API."""

from pathlib import Path

import pandas as pd
import requests
import streamlit as st

BASIS = Path(__file__).resolve().parent.parent
PARQUET = BASIS / "data_clean" / "daily_snow.parquet"
TEMPERATUR = BASIS / "data_clean" / "daily_temp.parquet"
STATIONEN = BASIS / "data_clean" / "stationen.csv"
API = "https://measurement-api.slf.ch/public/api/imis/daily-snow"
BULLETIN = "https://aws.slf.ch/api/bulletin/caaml/en/geojson"


@st.cache_data(ttl=1800, show_spinner=False)
def _hole_api(tage=7):
    """Fetches the last few days from the SLF API. Only 1, 3 or 7 are allowed."""
    antwort = requests.get(API, params={"period_in_days": tage}, timeout=20)
    antwort.raise_for_status()

    neu = pd.DataFrame(antwort.json())
    if neu.empty:
        return None

    neu["datum"] = pd.to_datetime(neu["measure_date"]).dt.normalize()
    neu["hyear"] = neu["datum"].dt.year + (neu["datum"].dt.month >= 10).astype(int)
    neu.loc[neu["HS"] < 0, "HS"] = 0.0
    return neu[["station_code", "datum", "hyear", "HS", "HN_1D"]]


@st.cache_data(ttl=1800, show_spinner="Loading snow data ...")
def lade_schnee():
    """Returns (data, live). live is False if the API could not be reached."""
    daten = pd.read_parquet(PARQUET)
    daten["station_code"] = daten["station_code"].astype(str)

    try:
        neu = _hole_api()
    except Exception:
        neu = None

    if neu is None:
        return daten.sort_values(["station_code", "datum"]).reset_index(drop=True), False

    daten = pd.concat([daten, neu], ignore_index=True)
    daten = (
        daten.drop_duplicates(["station_code", "datum"], keep="last")
        .sort_values(["station_code", "datum"])
        .reset_index(drop=True)
    )
    return daten, True


@st.cache_data(ttl=1800, show_spinner=False)
def lade_temperatur():
    """Daily air and snow surface temperatures per station."""
    temp = pd.read_parquet(TEMPERATUR)
    temp["station_code"] = temp["station_code"].astype(str)
    return temp


@st.cache_data(ttl=1800, show_spinner=False)
def lade_bulletin():
    """Current SLF avalanche bulletin as GeoJSON. None if unavailable."""
    try:
        antwort = requests.get(BULLETIN, timeout=15)
        antwort.raise_for_status()
        inhalt = antwort.json()
        if inhalt.get("features"):
            return inhalt
    except Exception:
        pass
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def lade_stationen(tage_aktiv=7):
    """Snow stations with coordinates and current snow depth."""
    daten, _ = lade_schnee()

    stationen = pd.read_csv(STATIONEN)
    stationen = stationen[stationen["typ"] == "schnee"].copy()

    letzte = daten.groupby("station_code")["datum"].max()
    aktiv = letzte[letzte >= letzte.max() - pd.Timedelta(days=tage_aktiv)].index
    stationen = stationen[stationen["station_code"].isin(aktiv)]

    neuste = (
        daten[daten["station_code"].isin(stationen["station_code"])]
        .sort_values("datum")
        .groupby("station_code")
        .last()
        .reset_index()[["station_code", "HS"]]
    )
    stationen = stationen.merge(neuste, on="station_code", how="left")
    stationen["HS"] = stationen["HS"].fillna(0).round(0)
    return stationen