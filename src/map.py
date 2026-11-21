"""The station map: every IMIS snow station, coloured by its current snow depth."""

import pydeck as pdk
import streamlit as st

TILES = "https://vectortiles.geo.admin.ch/styles"
BASEMAPS = {
    "Map": f"{TILES}/ch.swisstopo.lightbasemap.vt/style.json",
    "Aerial": f"{TILES}/ch.swisstopo.imagerybasemap.vt/style.json",
}

LEGEND = [
    ("#ffffff", "0", "Hiking boots"),
    ("#cfe3f3", "1–30", "Sacrifice your skis"),
    ("#94c2e3", "30–60", "Thin"),
    ("#4a90c4", "60–120", "Good"),
    ("#1f5f93", "120–200", "Great"),
    ("#0c3559", "200+", "Bottomless"),
]


def classify(hs):
    """Returns fill colour and outline colour for a snow depth in cm."""
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


def station_map(stations, selected, basemap="Map", height=600, key="station_map"):
    """Draws the map and returns the code of the station clicked on it, or None."""
    stations = stations.copy()
    classes = stations["HS"].apply(classify)
    stations["fill"] = [x[0] for x in classes]
    stations["outline"] = [x[1] for x in classes]

    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            id="stations",
            data=stations,
            get_position=["lon", "lat"],
            get_fill_color="fill",
            get_line_color="outline",
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

    if selected is not None:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="selection",
                data=stations[stations["station_code"] == selected],
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

    event = st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            map_style=BASEMAPS[basemap],
            initial_view_state=pdk.ViewState(
                latitude=46.80,
                longitude=8.23,
                zoom=7.0,
                min_zoom=6.8,
                max_zoom=16,
            ),
            tooltip={"text": "{name}\n{elevation} m a.s.l.\nSnow: {HS} cm"},
        ),
        on_select="rerun",
        selection_mode="single-object",
        height=height,
        key=key,
    )

    hits = event.selection.get("objects", {}).get("stations", [])
    return hits[0]["station_code"] if hits else None


def map_legend():
    """The colour scale below the map."""
    cells = "".join(
        "<div style='flex:1;padding-right:4px'>"
        f"<div style='height:11px;background:{colour};border:1px solid #d0d0d0'></div>"
        f"<div style='font-size:.68rem;color:#555555;margin-top:3px'>{span}</div>"
        f"<div style='font-size:.62rem;color:#9a9a9a;line-height:1.2'>{word}</div>"
        "</div>"
        for colour, span, word in LEGEND
    )
    st.markdown(
        f"<div style='display:flex;gap:2px;max-width:520px;margin-top:6px'>{cells}</div>"
        "<div style='font-size:.68rem;color:#808080;margin-top:8px'>"
        "Snow depth in cm"
        "</div>"
        "<div style='font-size:.68rem;color:#aaaaaa;margin-top:10px'>"
        "Map © swisstopo · Data © SLF"
        "</div>",
        unsafe_allow_html=True,
    )