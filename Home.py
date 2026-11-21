from pathlib import Path

import streamlit as st

from src.style import setup_page
from src.winterlines import DRAWING_CSS, STATION, load_winters, station_choices, winter_lines_svg

# Look of the home page only. Everything shared by all pages stays in src/style.py.
HOME_CSS = """
[data-testid="stMainBlockContainer"] { max-width: 1340px; padding-top: 3.4rem; padding-bottom: 2.5rem; }

/* the name sits in the empty sky above the autumn part of the drawing and lets the mouse through to it */
.st-key-home_head { position: relative; z-index: 2; pointer-events: none; }
.st-key-home_head h1 {
    font-size: 7.4rem !important; line-height: .86 !important; padding: 0; letter-spacing: -0.02em;
    -webkit-text-stroke: 14px #ffffff; paint-order: stroke fill;
}
.st-key-home_hero { margin-top: -7.2rem; }

.st-key-home_sub { margin-top: .4rem; }
.st-key-home_sub p.lede {
    font-family: 'Instrument Serif', Georgia, serif; font-size: 2rem; line-height: 1.15; color: #111111; margin: 0;
}
.st-key-home_sub p.note { font-size: .8rem; line-height: 1.5; color: #8c8c8c; margin: 0; text-align: right; white-space: nowrap; }

/* three tools: the name itself is the link, the whole column is clickable */
.st-key-home_tools { border-top: 1px solid #111111; margin-top: 1.1rem; }
.st-key-home_tools [data-testid="stHorizontalBlock"] { gap: 0; }
.st-key-home_tools [data-testid="stColumn"] + [data-testid="stColumn"] { border-left: 1px solid #e3e3e3; padding-left: 1.5rem; }
[class*="st-key-tool_"] { position: relative; padding: 1.15rem 1.5rem 1.2rem 0; }
[class*="st-key-tool_"] p.tag { font-size: .82rem; color: #8c8c8c; margin: 0; }
[class*="st-key-tool_"] [data-testid="stElementContainer"] { position: static; }
[class*="st-key-tool_"] [data-testid="stPageLink-NavLink"] {
    padding: 0; background: none !important; gap: .6rem; justify-content: flex-start;
}
[class*="st-key-tool_"] [data-testid="stPageLink-NavLink"]::before { content: ""; position: absolute; inset: 0; }
[class*="st-key-tool_"] [data-testid="stPageLink-NavLink"] p {
    font-family: 'Instrument Serif', Georgia, serif; font-size: 2.2rem; line-height: 1.1; color: #111111;
    background: linear-gradient(#111111, #111111) left bottom / 0 1px no-repeat; transition: background-size .35s ease;
}
[class*="st-key-tool_"] [data-testid="stPageLink-NavLink"]::after {
    content: "\\2192"; font-size: 1.5rem; color: #111111; transition: transform .35s ease;
}
[class*="st-key-tool_"]:hover [data-testid="stPageLink-NavLink"] p { background-size: 100% 1px; }
[class*="st-key-tool_"]:hover [data-testid="stPageLink-NavLink"]::after { transform: translateX(8px); }

/* phones */
@media (max-width: 640px) {
    .st-key-home_head h1 { font-size: 4.6rem !important; }
    .st-key-home_hero { margin-top: -1rem; }
    .st-key-home_sub p.note { text-align: left; }
    .st-key-home_tools [data-testid="stColumn"] + [data-testid="stColumn"] {
        border-left: 0; padding-left: 0; border-top: 1px solid #e3e3e3;
    }
}
"""

# Key, group, name, number of the page file in the pages folder, description
TOOLS = [
    ("history", "Touring", "Snow History", 1,
     "New snow and snow depth over the past weeks, to judge avalanche risk."),
    ("future", "Touring", "Snow Future", 2,
     "How long will the snow already lying last if none falls?"),
    ("finder", "Skiing", "Resort Finder", 3,
     "Set your weights on price, travel time, piste kilometres and mix, and it ranks resorts by exactly those."),
]


def page_file(number):
    """Path of the page whose file name starts with this number, for example pages/2_Snow_Future.py."""
    return f"pages/{next(Path(__file__).parent.glob(f'pages/{number}_*.py')).name}"


setup_page("SkiGuru")
st.markdown(f"<style>{HOME_CSS}{DRAWING_CSS}</style>", unsafe_allow_html=True)

# --- name ---
with st.container(key="home_head"):
    st.title("SkiGuru")

# --- the drawing goes here, as soon as the station is known ---
hero = st.container(key="home_hero")

# --- lede, station and source ---
choices = station_choices()                       # {station code: "Weissfluhjoch, 2'536 m"}
station = STATION
with st.container(key="home_sub"):
    left, right = st.columns([7, 5], vertical_alignment="bottom")
    left.markdown("<p class='lede'>Three tools for your next day on snow</p>", unsafe_allow_html=True)
    with right:
        pick, source = st.columns([4, 1], vertical_alignment="center")
        if choices:
            shared = st.session_state.get("station")                   # the station chosen in Snow History or Snow Future
            if shared in choices:
                st.session_state["home_station"] = shared
            elif st.session_state.get("home_station") not in choices:
                st.session_state["home_station"] = STATION if STATION in choices else next(iter(choices))
            if "home_pick" not in st.session_state:                    # first visit, or back from one of the tools
                st.session_state["home_pick"] = st.session_state["home_station"]
            station = pick.selectbox(
                "Station", list(choices), key="home_pick", format_func=choices.get, label_visibility="collapsed"
            )
            changed = station != st.session_state["home_station"]      # the station was changed just now
            if changed:
                st.session_state["home_turn"] = st.session_state.get("home_turn", 0) + 1
            st.session_state["home_station"] = station
            # The tools open with the same station. A station they show but this page cannot (too few winters)
            # is only replaced when the visitor picks another one here.
            if changed or shared is None or shared in choices:
                st.session_state["station"] = station
        source.markdown("<p class='note'>Data: SLF</p>", unsafe_allow_html=True)

# --- the drawing: one line per winter, the skier walks up the running one ---
winters = load_winters(station)
if winters:
    # The browser only plays the movement for parts of the page that are new. Streamlit reuses what is already
    # there, so the wrapper changes its name with every change of station. That makes the whole drawing new.
    tag = "section" if st.session_state.get("home_turn", 0) % 2 else "div"
    drawing = winter_lines_svg(winters, name=choices.get(station, station))
    hero.markdown(f"<{tag}>{drawing}</{tag}>", unsafe_allow_html=True)

# --- the three tools ---
with st.container(key="home_tools"):
    for column, (key, group, name, number, text) in zip(st.columns(3), TOOLS):
        with column:
            with st.container(key=f"tool_{key}"):
                st.markdown(f"<p class='tag'>{group}</p>", unsafe_allow_html=True)
                st.page_link(page_file(number), label=name)
                st.write(text)