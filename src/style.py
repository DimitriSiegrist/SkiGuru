"""Shared look for all SkiGuru pages."""

from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ICON = ASSETS / "icon.png"

STIL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&display=swap');

h1, h2, h3 {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-weight: 400 !important;
    letter-spacing: -0.015em;
}

h1 { font-size: 3.4rem !important; line-height: 1.05 !important; }

#MainMenu, footer { visibility: hidden; }

.st-key-gruppe_tour, .st-key-gruppe_piste {
    border: 1px solid #111111 !important;
    border-radius: 0 !important;
}

a, a:visited, a:hover { color: #111111 !important; }

hr { border-color: #ececec !important; }

.eyebrow {
    letter-spacing: .2em;
    text-transform: uppercase;
    font-size: .72rem;
    color: #8c8c8c;
    margin: 0 0 .4rem 0;
}
</style>
"""


def seite_aufsetzen(titel):
    """Sets page title, icon and style. Must be called first."""
    st.set_page_config(
        page_title=titel,
        page_icon=str(ICON),
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(STIL, unsafe_allow_html=True)