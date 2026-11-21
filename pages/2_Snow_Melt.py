import altair as alt
import pandas as pd
import streamlit as st

from src.data import load_snow, load_stations, load_temperature
from src.map import BASEMAPS, map_legend, station_map
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
if st.session_state.get("station") not in codes:
    st.session_state.station = stations.sort_values("HS")["station_code"].iloc[-1]
if "melt_last_click" not in st.session_state:
    st.session_state.melt_last_click = None

top_left, top_right = st.columns([1, 1], gap="large")
with top_left:
    basemap = st.radio("Map", list(BASEMAPS), horizontal=True)
with top_right:
    searched = st.selectbox(
        "Find a station",
        options=codes,
        index=codes.index(st.session_state.station),
        format_func=lambda c: f"{names[c]} ({c})",
    )
    if searched != st.session_state.station:
        st.session_state.station = searched
        st.rerun()

selected = st.session_state.station
station = stations[stations["station_code"] == selected].iloc[0]

history = snow[(snow["station_code"] == selected) & snow["HS"].notna()].sort_values("date")
today = history["date"].iloc[-1]
depth = float(history["HS"].iloc[-1])
fresh = fresh_stock(history, today)

map_col, side = st.columns([2, 1], gap="large")

with map_col:
    clicked = station_map(stations, selected, basemap, height=520, key="melt_map")
    map_legend()

# --- Process a new click on the map ---
if clicked is not None and clicked != st.session_state.melt_last_click:
    st.session_state.melt_last_click = clicked
    st.session_state.station = clicked
    st.rerun()

with side:
    st.subheader(station["name"])
    elevation = f"{station['elevation']:,.0f}".replace(",", "'")
    st.caption(f"{selected} · {elevation} m a.s.l.")
    st.metric(f"Snow depth · {today:%d %b}", f"{depth:.0f} cm")

    if depth <= 0:
        st.info("No snow at this station right now, so there is nothing to melt.")
        st.stop()

    # --- Scenario: how far ahead and how warm ---
    horizon = st.slider("Days without new snow", 7, 21, 14)
    first_day = today + pd.Timedelta(days=1)
    last_day = today + pd.Timedelta(days=horizon)

    # The temperature starts at what is normal at this station on these calendar days, over all years
    station_temp = temp[temp["station_code"] == selected]
    period = pd.date_range(first_day, last_day, freq="D").dayofyear
    same_days = station_temp[station_temp["date"].dt.dayofyear.isin(period)]

    label = "Mean air temperature of the coming days in °C"
    start = 0.0
    if not same_days.empty:
        normal = float(same_days["TA_mean"].mean())
        start = min(15.0, max(-15.0, round(normal * 2) / 2))
        label += f" (historical mean {normal:.1f} °C)"
    temperature = st.slider(label, -15.0, 15.0, start, 0.5)

# --- Forecast ---
curve = forecast(depth, fresh, [temperature] * horizon, first_day, model["coefficients"])
curve = pd.concat([pd.Series([depth], index=[today]), curve])
lower, upper = uncertainty(curve, model["errors"])

st.divider()
st.markdown("##### Forecast without new snow")

measured = "today" if today.date() == pd.Timestamp.now().date() else f"on {today.day} {today:%B}"
interval = f"95 % prediction interval: {lower.iloc[-1]:.0f} to {upper.iloc[-1]:.0f} cm"
if curve.iloc[-1] <= 0:
    gone = curve[curve <= 0].index[0]
    st.write(
        f"**{depth:.0f} cm** {measured}, gone by about **{gone.day} {gone:%B}** "
        f"({interval} on {last_day.day} {last_day:%B})."
    )
else:
    st.write(
        f"**{depth:.0f} cm** {measured}, about **{curve.iloc[-1]:.0f} cm** "
        f"on {last_day.day} {last_day:%B} ({interval})."
    )

# --- Method ---
with st.expander("How is the forecast calculated?"):
    coefficient = model["coefficients"]
    result = model["results"]
    error, t = result["std_errors"], result["t_values"]

    st.markdown(
        "On a day without new snow the depth falls because old snow settles, fresh snow "
        "settles faster and warmth melts it. One degree melts more in spring than in "
        "midwinter, because the sun is stronger."
    )

    st.markdown("**Model**")
    st.latex(
        r"HS_{i,t-1} - HS_{i,t} = \sigma \cdot HS_{i,t-1} + \nu \cdot F_{i,t-1} "
        r"+ \delta \cdot T^{+}_{i,t} \cdot R_t + \varepsilon_{i,t}"
    )
    st.markdown(
        r"""
| Symbol | Meaning | Source |
|---|---|---|
| $HS_{i,t}$ | Height of the snowpack at station $i$ on day $t$, in cm | SLF, IMIS stations, daily at 06:00 UTC |
| $F_{i,t}$ | Fresh snow stock in cm, $\sum_{k=0}^{20} 0.7^{k} \cdot HN_{i,t-k}$, where $HN$ is the height of new snow per day | SLF, modelled by SNOWPACK |
| $T^{+}_{i,t}$ | Mean air temperature of the day in °C, zero below freezing | SLF, IMIS stations, measured every 30 minutes |
| $R_t$ | Sun index, 0.22 on 21 December to 1 on 21 June: the solar energy possible on that day | Calculated from the date, FAO Paper 56 |
"""
    )

    st.markdown("**Results**")
    st.markdown("Dependent variable: daily decline of the snow depth in cm")
    st.markdown(
        rf"""
| | Coefficient | Std. error | t statistic |
|---|---|---|---|
| $\sigma$, snow depth the day before | {coefficient["HS_before"]:.4f} | {error["HS_before"]:.4f} | {t["HS_before"]:.1f} |
| $\nu$, fresh snow stock | {coefficient["fresh"]:.4f} | {error["fresh"]:.4f} | {t["fresh"]:.1f} |
| $\delta$, degrees above freezing × sun index | {coefficient["warm_sun"]:.4f} | {error["warm_sun"]:.4f} | {t["warm_sun"]:.1f} |
| Observations | {result["observations"]:,} | | |
| Stations, estimation sample | {result["stations"]} | | |
| $R^2$, estimation sample (winters {result["first_winter"]} to {result["last_winter"]}) | {result["r2"]:.3f} | | |
| Stations, out of sample | {result["stations_test"]} | | |
| $R^2$, out of sample (winters since {result["last_winter"] + 1}) | {result["r2_test"]:.3f} | | |
"""
    )
    st.markdown("Standard errors clustered by station and by day.")

    st.markdown("**Forecast**")
    st.markdown(
        f"Out of sample, over {result['spells_14']:,} periods of 14 days without snowfall, "
        f"the mean absolute forecast error is {result['error_14']:.0f} cm.\n\n"
        "The model assumes that no new snow falls and that every day is equally warm. "
        "Wind, rain, cloud cover and the slope are not taken into account.\n\n"
        "Sources: [SLF measurement data](https://measurement-data.slf.ch), "
        "[FAO Paper 56](https://www.fao.org/4/X0490e/x0490e07.htm), "
        "[Hock (1999)](https://doi.org/10.3189/S0022143000003087)."
    )

# --- Chart: hovering shows a point on the line with the expected depth and the interval ---
data = pd.DataFrame({
    "Date": curve.index,
    "Depth": curve.round(1).values,
    "Lower": lower.round(1).values,
    "Upper": upper.round(1).values,
})
data["Expected snow depth"] = data["Depth"].map("{:.0f} cm".format)
data["95 % interval"] = [f"[{low:.0f}, {high:.0f}] cm" for low, high in zip(data["Lower"], data["Upper"])]

base = alt.Chart(data).encode(x=alt.X("Date:T", title=None))
band = base.mark_area(opacity=0.18, color="#1f5f93").encode(
    y=alt.Y("Lower:Q", title="Snow depth in cm"), y2="Upper:Q"
)
line = base.mark_line(color="#1f5f93").encode(y="Depth:Q")

# The day nearest to the pointer is picked, wherever the pointer is in the chart
nearest = alt.selection_point(fields=["Date"], nearest=True, on="mouseover", empty=False)
tip = [alt.Tooltip("Date:T", format="%d %B"), "Expected snow depth:N", "95 % interval:N"]
picker = base.mark_rule(opacity=0).encode(tooltip=tip).add_params(nearest)
point = base.mark_circle(size=80, color="#1f5f93", opacity=1).encode(y="Depth:Q").transform_filter(nearest)

st.altair_chart((band + line + picker + point).properties(height=320), width="stretch")