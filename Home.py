import streamlit as st

from src.style import setup_page
from src.winterlines import DRAWING_CSS, format_metres, load_winters, ridgeline_svg, winter_label

# Look of the home page only. Everything shared by all pages stays in src/style.py.
HOME_CSS = """
[data-testid="stMainBlockContainer"] { max-width: 1340px; padding-top: 3.4rem; padding-bottom: 2.5rem; }

/* the name sits in the empty sky above the autumn part of the drawing */
.st-key-home_head { position: relative; z-index: 2; }
.st-key-home_head h1 {
    font-size: 7.4rem !important; line-height: .86 !important; padding: 0; letter-spacing: -0.02em;
    -webkit-text-stroke: 14px #ffffff; paint-order: stroke fill;
}
.st-key-home_head p.credit { font-size: .8rem; line-height: 1.5; color: #8c8c8c; margin: .6rem 0 0 0; text-align: right; }
.st-key-home_hero { margin-top: -7.2rem; }

.st-key-home_sub { margin-top: .4rem; }
.st-key-home_sub p.lede {
    font-family: 'Instrument Serif', Georgia, serif; font-size: 2rem; line-height: 1.15; color: #111111; margin: 0;
}
.st-key-home_sub p.note { font-size: .8rem; line-height: 1.5; color: #8c8c8c; margin: .35rem 0 0 0; }

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
    .st-key-home_head p.credit { text-align: left; }
    .st-key-home_hero { margin-top: -1rem; }
    .st-key-home_tools [data-testid="stColumn"] + [data-testid="stColumn"] {
        border-left: 0; padding-left: 0; border-top: 1px solid #e3e3e3;
    }
}
"""

TOOLS = [
    ("history", "Ski touring", "Snow History", "pages/1_Snow_History.py",
     "New snow and snow depth over the past weeks, to judge avalanche risk."),
    ("melt", "Ski touring", "Snow Future", "pages/2_Snow_Future.py",
     "How long will the snow already lying last if none falls?"),
    ("finder", "On piste", "Resort Finder", "pages/3_Resort_Finder.py",
     "Set your weights on price, travel time, piste kilometres and mix, and it ranks resorts by exactly those."),
]

setup_page("SkiGuru")
st.markdown(f"<style>{HOME_CSS}{DRAWING_CSS}</style>", unsafe_allow_html=True)

winters = load_winters()

# --- name and credit ---
with st.container(key="home_head"):
    left, right = st.columns([7, 5])
    left.title("SkiGuru")
    right.markdown(
        "<p class='credit'>Data Analysis with Python, HS26<br>Dimitri Siegrist &amp; Luisa Schnabel</p>",
        unsafe_allow_html=True,
    )

# --- the drawing: one line per winter ---
if winters:
    with st.container(key="home_hero"):
        st.markdown(ridgeline_svg(winters), unsafe_allow_html=True)

# --- lede and what the drawing shows ---
with st.container(key="home_sub"):
    left, right = st.columns([7, 5], vertical_alignment="bottom")
    left.markdown("<p class='lede'>Three tools for your next day on snow</p>", unsafe_allow_html=True)
    if winters:
        years = sorted(winters["seasons"])
        finished = len(years) - 1 if winters["running"] else len(years)
        height = f", {format_metres(winters['elevation'])} m" if winters["elevation"] else ""
        right.markdown(
            f"<p class='note'>Every line is one winter of snow depth on {winters['name']}{height}, "
            f"from 1 October to 31 July. {finished} winters since {winter_label(years[0])}, "
            "the latest in front. Data: SLF.</p>",
            unsafe_allow_html=True,
        )

# --- the three tools ---
with st.container(key="home_tools"):
    for column, (slug, group, name, page, text) in zip(st.columns(3), TOOLS):
        with column:
            with st.container(key=f"tool_{slug}"):
                st.markdown(f"<p class='tag'>{group}</p>", unsafe_allow_html=True)
                st.page_link(page, label=name)
                st.write(text)