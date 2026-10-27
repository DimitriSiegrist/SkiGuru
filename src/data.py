"""Schneedaten laden: Grundstock aus Parquet plus die letzten Tage aus der SLF-API."""

from pathlib import Path

import pandas as pd
import requests
import streamlit as st

BASIS = Path(__file__).resolve().parent.parent
PARQUET = BASIS / "data_clean" / "daily_snow.parquet"
STATIONEN = BASIS / "data_clean" / "stationen.csv"
API = "https://measurement-api.slf.ch/public/api/imis/daily-snow"


@st.cache_data(ttl=1800, show_spinner=False)
def _hole_api(tage=7):
    """Holt die letzten Tage von der SLF-API. Erlaubt sind nur 1, 3 oder 7."""
    antwort = requests.get(API, params={"period_in_days": tage}, timeout=20)
    antwort.raise_for_status()

    neu = pd.DataFrame(antwort.json())
    if neu.empty:
        return None

    neu["datum"] = pd.to_datetime(neu["measure_date"]).dt.normalize()
    neu["hyear"] = neu["datum"].dt.year + (neu["datum"].dt.month >= 10).astype(int)
    neu.loc[neu["HS"] < 0, "HS"] = 0.0
    return neu[["station_code", "datum", "hyear", "HS", "HN_1D"]]


@st.cache_data(ttl=1800, show_spinner="Lade Schneedaten ...")
def lade_schnee():
    """Gibt (daten, live) zurueck. live ist False, wenn die API nicht erreichbar war."""
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
def lade_stationen(tage_aktiv=7):
    """Schneestationen mit Koordinaten und aktuellem Schneestand."""
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