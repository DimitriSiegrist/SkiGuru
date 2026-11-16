import datetime as dt

import streamlit as st

from src.finder import consumer_surplus, load_data
from src.style import setup_page

setup_page("Resort Finder")

st.title("Resort Finder")
st.caption("Is a ski day worth the trip? Pilot: Engelberg-Titlis from Zürich HB.")


@st.cache_data(show_spinner=False)
def get_data():
    return load_data()


data = get_data()
RESORT = "Engelberg-Titlis"
dates = sorted(data["prices"]["date"].unique())
first, last = dt.date.fromisoformat(dates[0]), dt.date.fromisoformat(dates[-1])

# --- inputs ---
c1, c2, c3, c4 = st.columns(4)
day = c1.date_input("Ski day", value=first, min_value=first, max_value=last)
mode = c2.radio("Travel", ["train", "car"], horizontal=True)
travel_pass = c3.selectbox("Travel pass", ["none", "Halbtax", "GA"], index=1,
                           disabled=(mode == "car"))
v = c4.number_input("Value of time (CHF per hour)", min_value=0, max_value=200, value=20, step=5)
B0 = st.slider("What is a ski day as such worth to you? (B₀, CHF)", 0, 400, 150, step=10)

# --- result ---
r = consumer_surplus(data, RESORT, day.isoformat(), B0=B0, v=v,
                     mode=mode, travel_pass=travel_pass)

st.subheader(RESORT)
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Benefit B", f"CHF {r['B']:.0f}")
m2.metric("Day pass P", f"CHF {r['P']:.2f}")
m3.metric("Travel cost K", f"CHF {r['K']:.2f}")
m4.metric("Travel time", f"{r['T_h']:.1f} h", f"CHF {r['vT']:.0f} time cost", delta_color="off")
m5.metric("Consumer surplus", f"CHF {r['CS']:.0f}")

if r["CS"] >= 0:
    st.success(f"Worth the trip: you gain CHF {r['CS']:.0f} compared with staying home.")
else:
    st.warning(f"Not worth it: the trip costs you CHF {-r['CS']:.0f} more than it is worth to you.")

scraped = data["prices"]["scraped_on"].max()
st.caption(f"CS = B − P − K − v·T. Price: Pricenow, scraped on {scraped}. "
           "Snow: historical values at TIT2 Titlisboden (until the snow forecast is available). "
           "Train: Zürich HB → Engelberg incl. 10 min walk; car: OpenRouteService, CHF 0.28/km + CHF 10 parking.")