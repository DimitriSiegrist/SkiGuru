"""Gemeinsames Aussehen fuer alle Seiten von SkiGuru."""

from pathlib import Path

import streamlit as st

ICON = Path(__file__).resolve().parent.parent / "assets" / "skiguru_icon_192.png"

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

div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #e3e3e3 !important;
    border-radius: 0 !important;
    padding: 1.7rem 1.4rem 1.3rem !important;
    min-height: 250px;
    transition: border-color .18s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #111111 !important;
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

.kartensymbol {
    font-size: 1.5rem;
    line-height: 1;
    color: #111111;
    margin-bottom: .7rem;
}
</style>
"""


def seite_aufsetzen(titel):
    """Setzt Seitentitel, Icon und Stil. Muss als Erstes aufgerufen werden."""
    st.set_page_config(
        page_title=titel,
        page_icon=str(ICON),
        layout="wide",