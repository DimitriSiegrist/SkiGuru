import streamlit as st

from src.style import seite_aufsetzen

seite_aufsetzen("SkiGuru")

st.markdown(
    "<p class='eyebrow'>Data Analysis with Python · HS26 · "
    "Dimitri Siegrist & Luisa Schnabel</p>",
    unsafe_allow_html=True,
)
st.title("SkiGuru")
st.caption("Three tools for your next day on snow")

st.divider()

FEATURES = [
    ("pages/1_Snow_History.py", "❄", "Snow History",
     "New snow, snow depth and temperature over the last few weeks, "
     "to assess avalanche risk and whether a tour is feasible at all."),
    ("pages/2_Snow_Melt.py", "☼", "Snow Melt",
     "How long the existing snow will last if none falls. Very useful in spring."),
    ("pages/3_Resort_Finder.py", "❤", "Resort Finder",
     "You set your own weights on price, travel time from your starting point, "
     "snow conditions, piste kilometres and piste mix, and it ranks resorts by "
     "exactly those, instead of by a comparison site's criteria."),
]

spalten = st.columns(3, gap="medium")

for spalte, (pfad, symbol, titel, text) in zip(spalten, FEATURES):
    with spalte:
        with st.container(border=True):
            st.markdown(f"<div class='kartensymbol'>{symbol}</div>", unsafe_allow_html=True)
            st.subheader(titel)
            st.write(text)
            st.page_link(pfad, label="Open →")