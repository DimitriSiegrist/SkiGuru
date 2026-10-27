import pandas as pd
import pydeck as pdk
import streamlit as st

from src.data import lade_bulletin, lade_schnee, lade_stationen, lade_temperatur
from src.style import seite_aufsetzen

seite_aufsetzen("Snow History")

schnee, live = lade_schnee()
stationen = lade_stationen().copy()
temp = lade_temperatur()
bulletin = lade_bulletin()

stand = schnee["datum"].max()

if "station" not in st.session_state:
    st.session_state.station = None
if "letzter_klick" not in st.session_state:
    st.session_state.letzter_klick = None

# --- Avalanche danger levels, EAWS scale ---
STUFEN = {
    "low": (1, "Low", "#ccff66", "#111111"),
    "moderate": (2, "Moderate", "#ffff00", "#111111"),
    "considerable": (3, "Considerable", "#ff9900", "#111111"),
    "high": (4, "High", "#ff0000", "#ffffff"),
    "very_high": (5, "Very high", "#000000", "#ffffff"),
}


def meter(wert):
    """2677.0 -> 2'677"""
    return f"{wert:,.0f}".replace(",", "'")


def punkt_in_polygon(lon, lat, ring):
    """Ray casting test for a single ring of coordinates."""
    drin = False
    anzahl = len(ring)
    j = anzahl - 1
    for i in range(anzahl):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            schnitt = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < schnitt:
                drin = not drin
        j = i
    return drin


def region_finden(daten, lon, lat):
    """Returns the bulletin feature whose polygon contains the point."""
    for merkmal in daten.get("features", []):
        geometrie = merkmal.get("geometry") or {}
        typ = geometrie.get("type")
        koordinaten = geometrie.get("coordinates") or []

        if typ == "Polygon":
            polygone = [koordinaten]
        elif typ == "MultiPolygon":
            polygone = koordinaten
        else:
            continue

        for polygon in polygone:
            if polygon and punkt_in_polygon(lon, lat, polygon[0]):
                return merkmal
    return None


def hoechste_stufe(merkmal):
    """Highest danger level listed for this region."""
    gefunden = []
    for bewertung in merkmal.get("properties", {}).get("dangerRatings") or []:
        wert = bewertung.get("mainValue")
        if wert in STUFEN:
            gefunden.append(STUFEN[wert])
    if not gefunden:
        return None
    return max(gefunden, key=lambda s: s[0])


st.title("Snow History")
hinweis = "" if live else " Live update unavailable, showing stored data."
st.caption(
    f"{len(stationen)} IMIS snow stations. "
    f"Last measurement {stand:%d %B %Y}.{hinweis}"
)

# --- Controls above the map ---
BASIS = "https://vectortiles.geo.admin.ch/styles"
HINTERGRUND = {
    "Map": f"{BASIS}/ch.swisstopo.lightbasemap.vt/style.json",
    "Aerial": f"{BASIS}/ch.swisstopo.imagerybasemap.vt/style.json",
}

links_oben, rechts_oben = st.columns([1, 1], gap="large")

with links_oben:
    karten_wahl = st.radio("Map", list(HINTERGRUND), horizontal=True)

with rechts_oben:
    namen = dict(zip(stationen["station_code"], stationen["name"]))
    codes = stationen.sort_values("name")["station_code"].tolist()
    stand_index = (
        codes.index(st.session_state.station) + 1
        if st.session_state.station in codes
        else 0
    )
    gesucht = st.selectbox(
        "Find a station",
        options=[None] + codes,
        index=stand_index,
        format_func=lambda c: "Type a name ..." if c is None else f"{namen[c]} ({c})",
    )
    if gesucht is not None and gesucht != st.session_state.station:
        st.session_state.station = gesucht
        st.rerun()

gewaehlt = st.session_state.station


# --- Snow depth classes ---
def einstufen(hs):
    """Returns fill colour and outline colour."""
    if hs <= 0:
        return [255, 255, 255, 0], [120, 120, 120]
    if hs < 30:
        return [207, 227, 243, 235], [255, 255, 255]
    if hs < 60:
        return [148, 194, 227, 235], [255, 255, 255]
    if hs < 120:
        return [74, 144, 196, 235], [255, 255, 255]
    if hs < 200:
        return [31, 95, 147, 235], [255, 255, 255]
    return [12, 53, 89, 235], [255, 255, 255]


eingestuft = stationen["HS"].apply(einstufen)
stationen["fuellung"] = [x[0] for x in eingestuft]
stationen["rand"] = [x[1] for x in eingestuft]

karte_spalte, info_spalte = st.columns([2, 1], gap="large")

with karte_spalte:
    ebenen = [
        pdk.Layer(
            "ScatterplotLayer",
            id="stationen",
            data=stationen,
            get_position=["lon", "lat"],
            get_fill_color="fuellung",
            get_line_color="rand",
            get_radius=1600,
            radius_min_pixels=5,
            radius_max_pixels=14,
            get_line_width=1,
            line_width_min_pixels=1,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
        ),
    ]

    if gewaehlt is not None:
        ebenen.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="auswahl",
                data=stationen[stationen["station_code"] == gewaehlt],
                get_position=["lon", "lat"],
                get_fill_color=[0, 0, 0, 0],
                get_line_color=[17, 17, 17],
                get_radius=2800,
                radius_min_pixels=10,
                radius_max_pixels=22,
                get_line_width=2,
                line_width_min_pixels=2,
                stroked=True,
                filled=False,
                pickable=False,
            )
        )

    ereignis = st.pydeck_chart(
        pdk.Deck(
            layers=ebenen,
            map_style=HINTERGRUND[karten_wahl],
            initial_view_state=pdk.ViewState(
                latitude=46.80,
                longitude=8.23,
                zoom=7.0,
                min_zoom=6.8,
                max_zoom=16,
            ),
            tooltip={"text": "{name}\n{hoehe} m a.s.l.\nSnow: {HS} cm"},
        ),
        on_select="rerun",
        selection_mode="single-object",
        height=600,
        key="karte",
    )

    # --- Legend ---
    LEGENDE = [
        ("#ffffff", "0", "Hiking boots"),
        ("#cfe3f3", "1–30", "Sacrifice your skis"),
        ("#94c2e3", "30–60", "Thin"),
        ("#4a90c4", "60–120", "Good"),
        ("#1f5f93", "120–200", "Great"),
        ("#0c3559", "200+", "Bottomless"),
    ]
    felder = "".join(
        "<div style='flex:1;padding-right:4px'>"
        f"<div style='height:11px;background:{farbe};border:1px solid #d0d0d0'></div>"
        f"<div style='font-size:.68rem;color:#555555;margin-top:3px'>{bereich}</div>"
        f"<div style='font-size:.62rem;color:#9a9a9a;line-height:1.2'>{wort}</div>"
        "</div>"
        for farbe, bereich, wort in LEGENDE
    )
    st.markdown(
        f"<div style='display:flex;gap:2px;max-width:520px;margin-top:6px'>{felder}</div>"
        "<div style='font-size:.68rem;color:#808080;margin-top:8px'>"
        "Snow depth in cm at the station."
        "</div>"
        "<div style='font-size:.68rem;color:#aaaaaa;margin-top:10px'>"
        "Map © swisstopo · Data © SLF"
        "</div>",
        unsafe_allow_html=True,
    )

# --- Process a new click on the map ---
treffer = ereignis.selection.get("objects", {}).get("stationen", [])
if treffer:
    geklickt = treffer[0]["station_code"]
    if geklickt != st.session_state.letzter_klick:
        st.session_state.letzter_klick = geklickt
        st.session_state.station = geklickt
        st.rerun()

with info_spalte:
    if gewaehlt is None:
        st.info("Click a station on the map, or search for one above.")
    else:
        station = stationen[stationen["station_code"] == gewaehlt].iloc[0]
        alle = schnee[schnee["station_code"] == gewaehlt].sort_values("datum")
        letzte_woche = alle[alle["datum"] > stand - pd.Timedelta(days=7)]
        neu_7 = letzte_woche["HN_1D"].sum()

        st.subheader(station["name"])
        st.caption(f"{gewaehlt} · {meter(station['hoehe'])} m a.s.l.")

        if station["HS"] == 0:
            st.write("No snow at the station right now.")
        elif neu_7 > 0:
            st.write(
                f"**{station['HS']:.0f} cm** of snow, **{neu_7:.0f} cm** of which "
                "fell in the past week."
            )
        else:
            st.write(
                f"**{station['HS']:.0f} cm** of snow. Nothing new has fallen in the "
                "past week."
            )

        st.metric(f"Snow depth · {stand:%d %b}", f"{station['HS']:.0f} cm")
        st.metric("New snow · last 7 days", f"{neu_7:.0f} cm")

        # --- Avalanche bulletin ---
        st.markdown("###### Avalanche danger")

        stufe = None
        regionsname = None
        if bulletin is not None:
            try:
                merkmal = region_finden(
                    bulletin, float(station["lon"]), float(station["lat"])
                )
                if merkmal is not None:
                    stufe = hoechste_stufe(merkmal)
                    gebiete = merkmal.get("properties", {}).get("regions") or []
                    if gebiete:
                        regionsname = gebiete[0].get("name")
            except Exception:
                stufe = None

        if stufe is not None:
            nummer, bezeichnung, hintergrundfarbe, schriftfarbe = stufe
            ort = f" · {regionsname}" if regionsname else ""
            st.markdown(
                f"<div style='background:{hintergrundfarbe};color:{schriftfarbe};"
                "padding:.55rem .8rem;font-size:.95rem;font-weight:600;"
                f"border:1px solid #111111'>{nummer} · {bezeichnung}</div>"
                f"<div style='font-size:.68rem;color:#808080;margin-top:4px'>"
                f"Highest level forecast for this region{ort}.</div>",
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

if gewaehlt is None:
    st.stop()

station = stationen[stationen["station_code"] == gewaehlt].iloc[0]

st.divider()

# --- Period: fixed, avalanche-relevant windows ---
ZEITRAEUME = {
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

wahl = st.radio("Period", list(ZEITRAEUME), index=1, horizontal=True)
tage, erklaerung = ZEITRAEUME[wahl]
st.caption(erklaerung)

alle = schnee[schnee["station_code"] == gewaehlt].sort_values("datum")
saison = int(alle["hyear"].max())

if tage is None:
    saison_start = pd.Timestamp(year=saison - 1, month=10, day=1)
    saison_ende = pd.Timestamp(year=saison, month=6, day=30)
    reihe = alle[(alle["datum"] >= saison_start) & (alle["datum"] <= saison_ende)]
    zeitraum_text = (
        f"Season {saison - 1}/{str(saison)[-2:]}, 1 October to 30 June, "
        "the ski touring season"
    )
else:
    reihe = alle[alle["datum"] > stand - pd.Timedelta(days=tage)]
    zeitraum_text = f"{tage} days up to {stand:%d %B %Y}"

if reihe.empty:
    st.warning("No measurements for this station in the selected period.")
    st.stop()

# --- Snow depth ---
st.markdown("##### Snow depth")
st.caption(f"Total snow lying at the station, in cm. {zeitraum_text}.")

linie = reihe.rename(columns={"datum": "Date", "HS": "Snow depth (cm)"})
linie["Snow depth (cm)"] = linie["Snow depth (cm)"].astype("float64").round(1)
st.line_chart(linie.set_index("Date")["Snow depth (cm)"], height=260)

# --- New snow ---
st.markdown("##### New snow per day")
st.caption(f"Fresh snowfall in cm. {zeitraum_text}.")

with st.expander("How is new snow per day calculated?"):
    st.markdown(
        "The station only measures one thing: the total depth of the snowpack. "
        "New snow is not simply the change in that number, because the pack settles "
        "and melts while fresh snow lands on top of it. Twenty centimetres of new snow "
        "can lift the measured depth by only fifteen, and on a warm spring day the depth "
        "can even fall while it is snowing.\n\n"
        "SLF's **SNOWPACK** model resolves this. It simulates the snowpack layer by layer "
        "from the station's own measurements of air temperature, humidity, wind and "
        "radiation, calculates how far each layer sank or melted, and attributes whatever "
        "is left over to fresh snowfall.\n\n"
        "The figure shown here is therefore modelled rather than measured. It is the same "
        "model that underpins the national avalanche bulletin."
    )

balken = reihe.rename(columns={"datum": "Date", "HN_1D": "New snow (cm)"})
balken["New snow (cm)"] = balken["New snow (cm)"].astype("float64").round(1)
st.bar_chart(balken.set_index("Date")["New snow (cm)"], height=200)

# --- Air temperature ---
st.markdown("##### Air temperature")

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

t_reihe = temp[
    (temp["station_code"] == gewaehlt)
    & (temp["datum"] >= reihe["datum"].min())
    & (temp["datum"] <= reihe["datum"].max())
].sort_values("datum")

if t_reihe.empty:
    st.caption("No temperature data available for this station.")
else:
    ueber_null = int((t_reihe["TA_mean"] > 0).sum())
    st.caption(
        f"Daily mean, minimum and maximum in °C. The daily mean was above freezing "
        f"on {ueber_null} of {len(t_reihe)} days in this period."
    )

    lang = t_reihe.melt(
        id_vars="datum",
        value_vars=["TA_max", "TA_mean", "TA_min"],
        var_name="Series",
        value_name="Temperature (°C)",
    )
    lang["Series"] = lang["Series"].map(
        {"TA_max": "Max", "TA_mean": "Mean", "TA_min": "Min"}
    )
    lang["Temperature (°C)"] = lang["Temperature (°C)"].astype("float64").round(1)
    lang = lang.rename(columns={"datum": "Date"})

    st.line_chart(
        lang,
        x="Date",
        y="Temperature (°C)",
        color="Series",
        height=240,
    )