import pandas as pd
import streamlit as st

from src.data import (
    load_bulletin,
    load_snow,
    load_stations,
    load_temperature,
    load_temperature_live,
)
from src.map import BASEMAPS, map_legend, station_map
from src.style import setup_page

setup_page("Snow History")

snow, live = load_snow()
stations = load_stations()
temp = load_temperature()
bulletin = load_bulletin()

latest = snow["date"].max()

if "station" not in st.session_state:
    st.session_state.station = None
if "last_click" not in st.session_state:
    st.session_state.last_click = None

# --- Avalanche danger levels, EAWS scale ---
LEVELS = {
    "low": (1, "Low", "#ccff66", "#111111"),
    "moderate": (2, "Moderate", "#ffff00", "#111111"),
    "considerable": (3, "Considerable", "#ff9900", "#111111"),
    "high": (4, "High", "#ff0000", "#ffffff"),
    "very_high": (5, "Very high", "#000000", "#ffffff"),
}


def format_metres(value):
    """2677.0 -> 2'677"""
    return f"{value:,.0f}".replace(",", "'")


def point_in_polygon(lon, lat, ring):
    """Ray casting test for a single ring of coordinates."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            crossing = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < crossing:
                inside = not inside
        j = i
    return inside


def find_region(data, lon, lat):
    """Returns the bulletin feature whose polygon contains the point."""
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        kind = geometry.get("type")
        coordinates = geometry.get("coordinates") or []

        if kind == "Polygon":
            polygons = [coordinates]
        elif kind == "MultiPolygon":
            polygons = coordinates
        else:
            continue

        for polygon in polygons:
            if polygon and point_in_polygon(lon, lat, polygon[0]):
                return feature
    return None


def highest_level(feature):
    """Highest danger level listed for this region."""
    found = []
    for rating in feature.get("properties", {}).get("dangerRatings") or []:
        value = rating.get("mainValue")
        if value in LEVELS:
            found.append(LEVELS[value])
    if not found:
        return None
    return max(found, key=lambda s: s[0])


st.title("Snow History")
note = "" if live else " Live update unavailable, showing stored data."
st.caption(f"New snow and snow depth over the past weeks, to judge avalanche risk.{note}")

# --- Controls above the map ---
top_left, top_right = st.columns([1, 1], gap="large")

with top_left:
    basemap = st.radio("Map", list(BASEMAPS), horizontal=True)

with top_right:
    names = dict(zip(stations["station_code"], stations["name"]))
    codes = stations.sort_values("name")["station_code"].tolist()
    current_index = (
        codes.index(st.session_state.station) + 1
        if st.session_state.station in codes
        else 0
    )
    searched = st.selectbox(
        "Find a station",
        options=[None] + codes,
        index=current_index,
        format_func=lambda c: "Type a name ..." if c is None else f"{names[c]} ({c})",
    )
    if searched is not None and searched != st.session_state.station:
        st.session_state.station = searched
        st.rerun()

selected = st.session_state.station

map_col, info_col = st.columns([2, 1], gap="large")

with map_col:
    clicked = station_map(stations, selected, basemap)
    map_legend()

# --- Process a new click on the map ---
if clicked is not None and clicked != st.session_state.last_click:
    st.session_state.last_click = clicked
    st.session_state.station = clicked
    st.rerun()

with info_col:
    if selected is None:
        st.info("Click a station on the map, or search for one above.")
    else:
        station = stations[stations["station_code"] == selected].iloc[0]
        history = snow[snow["station_code"] == selected].sort_values("date")
        last_week = history[history["date"] > latest - pd.Timedelta(days=7)]
        new_7 = last_week["HN_1D"].sum()

        st.subheader(station["name"])
        st.caption(f"{selected} · {format_metres(station['elevation'])} m a.s.l.")

        st.metric(f"Snow depth · {latest:%d %b}", f"{station['HS']:.0f} cm")
        st.metric("New snow · last 7 days", f"{new_7:.0f} cm")

        # --- Avalanche bulletin ---
        st.markdown("###### Avalanche danger")

        level = None
        region_name = None
        if bulletin is not None:
            try:
                feature = find_region(
                    bulletin, float(station["lon"]), float(station["lat"])
                )
                if feature is not None:
                    level = highest_level(feature)
                    regions = feature.get("properties", {}).get("regions") or []
                    if regions:
                        region_name = regions[0].get("name")
            except Exception:
                level = None

        if level is not None:
            number, label, background, text_colour = level
            place = f" · {region_name}" if region_name else ""
            st.markdown(
                f"<div style='background:{background};color:{text_colour};"
                "padding:.55rem .8rem;font-size:.95rem;font-weight:600;"
                f"border:1px solid #111111'>{number} · {label}</div>"
                f"<div style='font-size:.68rem;color:#808080;margin-top:4px'>"
                f"Highest level forecast for this region{place}.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption(
                "No current bulletin for this location. Outside winter the bulletin "
                "is issued only after heavy snowfall."
            )

        st.link_button(
            "Open the avalanche bulletin →",
            "https://whiterisk.ch/en/conditions/bulletin",
        )

        st.caption(
            "SkiGuru shows measurements, not a danger assessment. SLF publishes the "
            "bulletin daily at 17:00 for the following day, valid until 17:00; the "
            "English version follows by 18:00. In winter it is renewed at 08:00 "
            "whenever level 3 or above was forecast anywhere in Switzerland."
        )

if selected is None:
    st.stop()

station = stations[stations["station_code"] == selected].iloc[0]

st.divider()

# --- Period: fixed, avalanche-relevant windows ---
PERIODS = {
    "Last 2 weeks": (
        14,
        "What has landed recently and what the wind did with it. This is the window "
        "the avalanche bulletin is mostly about.",
    ),
    "Last 4 weeks": (
        28,
        "Enough time to see whether the snow has settled and bonded, or whether fresh "
        "snow fell onto an old crust.",
    ),
    "Whole season": (
        None,
        "Weak layers that form early in the winter can still release avalanches months "
        "later, so the whole season matters, not only the past few weeks.",
    ),
}

choice = st.radio("Period", list(PERIODS), index=1, horizontal=True)
days, explanation = PERIODS[choice]
st.caption(explanation)

history = snow[snow["station_code"] == selected].sort_values("date")
season = int(history["hyear"].max())

if days is None:
    season_start = pd.Timestamp(year=season - 1, month=10, day=1)
    season_end = pd.Timestamp(year=season, month=6, day=30)
    series = history[(history["date"] >= season_start) & (history["date"] <= season_end)]
else:
    series = history[history["date"] > latest - pd.Timedelta(days=days)]

if series.empty:
    st.warning("No measurements for this station in the selected period.")
    st.stop()

# --- Snow depth ---
st.markdown("##### Snow depth")

line = series.rename(columns={"date": "Date", "HS": "Snow depth in cm"})
line["Snow depth in cm"] = line["Snow depth in cm"].astype("float64").round(1)
st.line_chart(line.set_index("Date")["Snow depth in cm"], height=260, y_label="Snow depth in cm")

# --- New snow ---
st.markdown("##### New snow per day")

with st.expander("How is new snow per day calculated?"):
    st.markdown(
        "The station measures the total depth of the snowpack, but new snow is not "
        "simply the change in that number, because the pack settles and melts while "
        "fresh snow lands on top of it. Twenty centimetres of new snow can lift the "
        "measured depth by only fifteen, and on a warm spring day the depth can even "
        "fall while it is snowing.\n\n"
        "SLF's **SNOWPACK** model resolves this. It simulates the snowpack layer by layer "
        "from the station's own measurements of air temperature, humidity, wind and "
        "radiation, calculates how far each layer sank or melted, and attributes whatever "
        "is left over to fresh snowfall.\n\n"
        "The figure shown here is therefore modelled based on the station's measured "
        "snow depth and weather data.\n\n"
        "Source: [Snow cover modelling, SLF]"
        "(https://www.slf.ch/en/snow/snowpack/snow-cover-modelling/)"
    )

bars = series.rename(columns={"date": "Date", "HN_1D": "New snow in cm"})
bars["New snow in cm"] = bars["New snow in cm"].astype("float64").round(1)
if bars["New snow in cm"].notna().any():
    st.bar_chart(bars.set_index("Date")["New snow in cm"], height=200, y_label="New snow in cm")
else:
    st.caption("**SLF publishes no new snow figure for this station in this period.**")

# --- Air temperature ---
st.markdown("##### Temperature")

with st.expander("How is the daily temperature calculated?"):
    st.markdown(
        "The station records air temperature every 30 minutes, so a full day has 48 "
        "readings, and the daily mean is the average of all of them.\n\n"
        "A day here runs from 7 in the morning to 7 the next morning, not midnight to "
        "midnight. That is when SLF reads the snow depth, at dawn, when the pack is at "
        "its coldest and has settled overnight. Using the same hours means the "
        "temperature and the snow describe exactly the same 24 hours.\n\n"
        "IMIS stations are powered by a solar panel and a battery, which rules out a "
        "heated, fan-ventilated sensor. Without a fan, sunshine warms the sensor "
        "housing itself, so on a calm bright day it reports its own temperature rather "
        "than the air's and can read a few degrees too warm. And if the panel stays "
        "iced over for weeks, the battery runs flat and the station stops reporting "
        "altogether. Readings are missing on about 7 per cent of days."
    )

station_temp = temp[temp["station_code"] == selected]

# The stored data is refreshed twice a week; the last days come live from the API
live_temp = load_temperature_live(selected)
if live_temp is not None:
    station_temp = pd.concat([station_temp, live_temp], ignore_index=True)
    station_temp = station_temp.drop_duplicates("date", keep="last")

temp_series = station_temp[
    (station_temp["date"] >= series["date"].min())
    & (station_temp["date"] <= series["date"].max())
].sort_values("date")

if temp_series.empty:
    st.caption("No temperature data available for this station.")
else:
    long = temp_series.melt(
        id_vars="date",
        value_vars=["TA_max", "TA_mean", "TA_min"],
        var_name="Series",
        value_name="Temperature in °C",
    )
    long["Series"] = long["Series"].map(
        {"TA_max": "Max", "TA_mean": "Mean", "TA_min": "Min"}
    )
    long["Temperature in °C"] = long["Temperature in °C"].astype("float64").round(1)
    long = long.rename(columns={"date": "Date"})

    st.line_chart(
        long,
        x="Date",
        y="Temperature in °C",
        y_label="Temperature in °C",
        color="Series",
        height=240,
    )