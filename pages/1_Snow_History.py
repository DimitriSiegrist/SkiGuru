import pandas as pd
import pydeck as pdk
import streamlit as st

from src.data import lade_schnee, lade_stationen
from src.style import seite_aufsetzen

seite_aufsetzen("Snow History")

schnee, live = lade_schnee()
stationen = lade_stationen()

stand = schnee["datum"].max()


def meter(wert):
    """2677.0 -> 2'677"""
    return f"{wert:,.0f}".replace(",", "'")


st.title("Snow History")
hinweis = "" if live else " Live update unavailable, showing stored data."
st.caption(
    f"{len(stationen)} IMIS snow stations. "
    f"Last measurement {stand:%d %B %Y}.{hinweis} Click a station on the map."
)


# --- Point colour: little snow light, deep snow dark ---
def farbe(hs):
    anteil = min(hs / 150, 1.0)
    grau = int(200 - 180 * anteil)
    return [grau, grau, grau]


stationen["farbe"] = stationen["HS"].apply(farbe)

ebene = pdk.Layer(
    "ScatterplotLayer",
    data=stationen,
    id="stationen",
    get_position=["lon", "lat"],
    get_fill_color="farbe",
    get_radius=1800,
    radius_min_pixels=5,
    radius_max_pixels=14,
    pickable=True,
    auto_highlight=True,
)

ereignis = st.pydeck_chart(
    pdk.Deck(
        layers=[ebene],
        initial_view_state=pdk.ViewState(latitude=46.72, longitude=8.3, zoom=6.6),
        tooltip={"text": "{name}\n{hoehe} m a.s.l.\nSnow: {HS} cm"},
    ),
    on_select="rerun",
    selection_mode="single-object",
    height=460,
)

gewaehlt = None
treffer = ereignis.selection.get("objects", {}).get("stationen", [])
if treffer:
    gewaehlt = treffer[0]["station_code"]

if gewaehlt is None:
    st.info("No station selected yet. Click a point on the map.")
    st.stop()

station = stationen[stationen["station_code"] == gewaehlt].iloc[0]

st.divider()
st.subheader(f"{station['name']} ({gewaehlt})")

# --- Period: fixed, avalanche-relevant windows ---
ZEITRAEUME = {
    "Last 2 weeks": 14,
    "Last 4 weeks": 28,
    "Whole season": None,
}
wahl = st.radio("Period", list(ZEITRAEUME), index=1, horizontal=True)
tage = ZEITRAEUME[wahl]

alle = schnee[schnee["station_code"] == gewaehlt].sort_values("datum")
saison = int(alle["hyear"].max())

if tage is None:
    reihe = alle[alle["hyear"] == saison]
    zeitraum_text = f"Season {saison - 1}/{str(saison)[-2:]}, since 1 October"
else:
    reihe = alle[alle["datum"] > stand - pd.Timedelta(days=tage)]
    zeitraum_text = f"{tage} days up to {stand:%d %B %Y}"

if reihe.empty:
    st.warning("No measurements for this station in the selected period.")
    st.stop()

letzte_woche = alle[alle["datum"] > stand - pd.Timedelta(days=7)]
neu_7 = letzte_woche["HN_1D"].sum()
neu_zeitraum = reihe["HN_1D"].sum()

# --- One sentence in plain language ---
if station["HS"] == 0:
    satz = (
        f"**{station['name']}** sits at {meter(station['hoehe'])} m. "
        f"No snow at the station right now."
    )
elif neu_7 > 0:
    satz = (
        f"**{station['name']}** sits at {meter(station['hoehe'])} m and currently has "
        f"**{station['HS']:.0f} cm** of snow, **{neu_7:.0f} cm** of which fell in the past week."
    )
else:
    satz = (
        f"**{station['name']}** sits at {meter(station['hoehe'])} m and currently has "
        f"**{station['HS']:.0f} cm** of snow. Nothing new has fallen in the past week."
    )

st.markdown(satz)

a, b, c = st.columns(3)
a.metric(f"Snow depth · {stand:%d %b}", f"{station['HS']:.0f} cm")
b.metric("New snow · last 7 days", f"{neu_7:.0f} cm")
c.metric(f"New snow · {wahl.lower()}", f"{neu_zeitraum:.0f} cm")

# --- Snow depth ---
st.markdown("##### Snow depth")
st.caption(f"Total snow lying at the station, in cm. {zeitraum_text}.")

linie = reihe.rename(columns={"datum": "Date", "HS": "Snow depth (cm)"})
st.line_chart(linie.set_index("Date")["Snow depth (cm)"], height=260)

# --- New snow ---
st.markdown("##### New snow per day")
st.caption(
    "Snow that fell in the preceding 24 hours, in cm. "
    "Modelled by the SNOWPACK model from the station's measurements, not measured directly."
)

balken = reihe.rename(columns={"datum": "Date", "HN_1D": "New snow (cm)"})
st.bar_chart(balken.set_index("Date")["New snow (cm)"], height=200)