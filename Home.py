import streamlit as st

st.set_page_config(page_title="SkiGuru", page_icon="🏔️", layout="wide")

st.title("🏔️ SkiGuru")
st.caption("Vier Werkzeuge für den nächsten Skitag")

st.divider()

st.markdown(
    """
    Wir bauen eine App mit vier Funktionen, die wir uns auf anderen
    Skiseiten gewünscht hätten. Zwei fürs Tourengehen, zwei für die Piste.

    **Snow History** zeigt Neuschnee und Schneehöhe der letzten Wochen.

    **Snow Melt** schätzt, wie lange der Schnee noch liegt.

    **Price Explorer** findet die günstigen Tage an einem Skigebiet.

    **Resort Finder** rangiert Skigebiete nach deinen eigenen Gewichten.

    Links in der Navigation geht es los.
    """
)

st.divider()
st.caption("Projekt von Dimitri Siegrist und Luisa Schnabel · Data Analysis with Python, HS26")