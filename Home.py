import streamlit as st

from src.style import ASSETS, seite_aufsetzen

seite_aufsetzen("SkiGuru")

st.markdown(
    "<p class='eyebrow'>Data Analysis with Python · HS26 · "
    "Dimitri Siegrist & Luisa Schnabel</p>",
    unsafe_allow_html=True,
)
st.title("SkiGuru")
st.caption("Three tools for your next day on snow")

st.write("")

links, rechts = st.columns([2, 1], gap="medium")

with links:
    st.image(str(ASSETS / "ski_touring.png"), width=96)
    with st.container(border=True, height=270, key="gruppe_tour"):
        st.markdown("### Ski touring")
        st.caption("Is the tour on, and how long will the snow hold?")

        a, b = st.columns(2, gap="medium")
        with a:
            st.markdown("**Snow History**")
            st.write(
                "New snow and snow depth over the past weeks, to judge avalanche "
                "risk and whether a tour is feasible at all."
            )
            st.page_link("pages/1_Snow_History.py", label="Open →")
        with b:
            st.markdown("**Snow Melt**")
            st.write(
                "How long the snow already lying will last if none falls. "
                "Most useful in spring."
            )
            st.page_link("pages/2_Snow_Melt.py", label="Open →")

with rechts:
    st.image(str(ASSETS / "ski_downhill.png"), width=96)
    with st.container(border=True, height=270, key="gruppe_piste"):
        st.markdown("### On piste")
        st.caption("Which resort fits your day?")

        st.markdown("**Resort Finder**")
        st.write(
            "Set your weights on price, travel time, piste kilometres and mix, and it ranks resorts by exactly those."
        )
        st.page_link("pages/3_Resort_Finder.py", label="Open →")