import datetime as dt

import streamlit as st

from src.finder import (DEFAULT_IMPORTANCE, DEFAULT_TOTAL, consumer_surplus, load_data,
                        merge_tables, weights_from_importance)
from src.style import setup_page

setup_page("Resort Finder")

st.title("Resort Finder")
st.caption("Is a ski day worth the trip? Pilot: Engelberg-Titlis from Zürich HB.")


@st.cache_data(show_spinner=False)
def get_data():
    return merge_tables(load_data())


data = get_data()
RESORT = "Engelberg-Titlis"
dates = sorted(data.dropna(subset=["price"])["date"].unique())
first, last = dt.date.fromisoformat(dates[0]), dt.date.fromisoformat(dates[-1])

# share the resort's snow station with the snow pages (same key as pages 1 and 2);
# only when the finder's resort changes, so a station picked on a snow page is not overwritten
if st.session_state.get("finder_resort") != RESORT:
    st.session_state.finder_resort = RESORT
    st.session_state.station = data.loc[data["resort"] == RESORT, "station_code"].iloc[0]

# --- sidebar inputs (task 17.1) ---
with st.sidebar:
    st.header("Your ski day")
    st.caption("Start point: Zürich HB")
    day = st.date_input("Ski day", value=first, min_value=first, max_value=last)
    mode = st.radio("Travel", ["train", "car"], horizontal=True)
    travel_pass = st.selectbox("Travel pass", ["none", "Halbtax", "GA"], index=1)
    v = st.number_input("Value of time (CHF per hour)", min_value=0, max_value=200, value=20, step=5)
    use_budget = st.checkbox("Set a budget")
    budget = st.number_input("Budget for day pass + travel (CHF)", min_value=0, max_value=500,
                             value=150, step=10, disabled=not use_budget)
    budget = budget if use_budget else None   # None → no filter in rank_resorts()
    B0 = st.slider("What is a ski day as such worth to you? (B₀, CHF)", 0, 400, 150, step=10)

    st.header("What matters to you")
    level = st.radio("Your level", ["beginner", "intermediate", "expert"], index=1, horizontal=True)
    total = st.number_input("How much more is a day at your ideal resort worth than at the most basic one? (CHF)",
                            min_value=0, max_value=1000, value=DEFAULT_TOTAL, step=10)
    st.caption("Importance: 0 = not important … 5 = very important")
    LABELS = {"piste_km": "Piste km", "vertical_drop": "Vertical drop", "top_alt": "Top altitude",
              "snowmaking_share": "Snowmaking", "difficulty": "Pistes at your level",
              "x_snow_depth": "Snow depth", "x_new_snow": "New snow",
              "rating_family": "Family friendly", "rating_freeride": "Freeride", "rating_park": "Snow park"}
    importance = {k: st.slider(label, 0, 5, DEFAULT_IMPORTANCE[k]) for k, label in LABELS.items()}

# --- result ---
weights = weights_from_importance(importance, total)
r = consumer_surplus(data, day.isoformat(), B0=B0, v=v, mode=mode, travel_pass=travel_pass,
                     level=level, weights=weights).set_index("resort").loc[RESORT]

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

scraped = data["scraped_on"].dropna().max()
st.caption(f"CS = B − P − K − v·T. Price: Pricenow, scraped on {scraped}. "
           "Snow: historical values at TIT2 Titlisboden (until the snow forecast is available). "
           "Train: Zürich HB → Engelberg incl. 10 min walk; car: OpenRouteService, CHF 0.28/km + CHF 10 parking.")