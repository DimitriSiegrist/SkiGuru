import altair as alt
import pandas as pd
import streamlit as st

from src.data import load_snow, load_stations, load_temperature
from src.melt import forecast, fresh_stock, load_model, uncertainty
from src.style import setup_page

setup_page("Snow Melt")

snow, live = load_snow()
stations = load_stations()
temp = load_temperature()
model = load_model()

st.title("Snow Melt")
st.caption("How long will the snow already lying last if none falls?")

# --- Station: the one chosen on another page, otherwise the one with the most snow ---
names = dict(zip(stations["station_code"], stations["name"]))
codes = stations.sort_values("name")["station_code"].tolist()
deepest = stations.sort_values("HS")["station_code"].iloc[-1]
current = st.session_state.get("station") or deepest

selected = st.selectbox(
    "Station",
    options=codes,
    index=codes.index(current) if current in codes else 0,
    format_func=lambda c: f"{names[c]} ({c})",
)
st.session_state.station = selected

history = snow[(snow["station_code"] == selected) & snow["HS"].notna()].sort_values("date")
today = history["date"].iloc[-1]
depth = float(history["HS"].iloc[-1])
fresh = fresh_stock(history, today)

if depth <= 0:
    st.info(f"No snow at {names[selected]} right now, so there is nothing to melt.")
    st.stop()

# --- Scenario: how warm and how far ahead ---
# The slider starts at what is normal at this station in the two weeks ahead, over all years
station_temp = temp[temp["station_code"] == selected]
ahead = pd.date_range(today + pd.Timedelta(days=1), periods=14, freq="D").dayofyear
same_season = station_temp[station_temp["date"].dt.dayofyear.isin(ahead)]
past_week = station_temp[station_temp["date"] > today - pd.Timedelta(days=7)]

normal = 0.0 if same_season.empty else float(same_season["TA_mean"].mean())
start = min(15.0, max(-15.0, round(normal * 2) / 2))

left, right = st.columns(2, gap="large")
with left:
    temperature = st.slider("Mean air temperature of the coming days (°C)", -15.0, 15.0, start, 0.5)
    note = ""
    if not same_season.empty:
        years = same_season["date"].dt.year.nunique()
        note = f"Starts at the mean of these two weeks over {years} years at this station, {normal:.1f} °C."
    if not past_week.empty:
        note += f" The past week averaged {past_week['TA_mean'].mean():.1f} °C."
    st.caption(note.strip())
with right:
    horizon = st.slider("Days ahead", 7, 21, 14)

# --- Forecast ---
first_day = today + pd.Timedelta(days=1)
curve = forecast(depth, fresh, [temperature] * horizon, first_day, model["coefficients"])
curve = pd.concat([pd.Series([depth], index=[today]), curve])
lower, upper = uncertainty(curve, model["errors"])

left_after = curve.iloc[-1]
if left_after <= 0:
    gone = curve[curve <= 0].index[0]
    st.write(
        f"**{depth:.0f} cm** at {names[selected]} on {today:%d %B}. At {temperature:.1f} °C "
        f"and without new snow it is gone by **{gone:%d %B}**."
    )
else:
    st.write(
        f"**{depth:.0f} cm** at {names[selected]} on {today:%d %B}. At {temperature:.1f} °C "
        f"and without new snow, **{left_after:.0f} cm** are left after {horizon} days, "
        f"very likely between {lower.iloc[-1]:.0f} and {upper.iloc[-1]:.0f} cm."
    )

data = pd.DataFrame({
    "Date": curve.index,
    "Snow depth (cm)": curve.round(1).values,
    "Lower": lower.round(1).values,
    "Upper": upper.round(1).values,
})
base = alt.Chart(data).encode(x=alt.X("Date:T", title=None))
band = base.mark_area(opacity=0.18, color="#1f5f93").encode(
    y=alt.Y("Lower:Q", title="Snow depth (cm)"), y2="Upper:Q"
)
line = base.mark_line(color="#1f5f93").encode(
    y="Snow depth (cm):Q", tooltip=["Date:T", "Snow depth (cm):Q", "Lower:Q", "Upper:Q"]
)
st.altair_chart((band + line).properties(height=320), width="stretch")
st.caption(
    "The line is the forecast. The shaded band is where the measured depth ended up in "
    "95 of 100 forecasts over real spells without new snow since winter 2020."
)