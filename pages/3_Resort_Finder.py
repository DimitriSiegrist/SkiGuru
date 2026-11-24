import datetime as dt

import streamlit as st

from src.finder import (DEFAULT_IMPORTANCE, DEFAULT_TOTAL, consumer_surplus, load_data,
                        merge_tables, rank_resorts, weights_from_importance)
from src.style import setup_page

setup_page("Resort Finder")

st.title("Resort Finder")
st.caption("Which ski resort is worth the trip from Zürich HB on your day?")


@st.cache_data(show_spinner=False)
def get_data():
    return merge_tables(load_data())


data = get_data()
RESORT = "Engelberg-Titlis"
dates = sorted(data.dropna(subset=["price"])["date"].unique())
first, last = dt.date.fromisoformat(dates[0]), dt.date.fromisoformat(dates[-1])

# --- sidebar inputs (task 17.1) ---
with st.sidebar:
    st.header("Your ski day")
    st.caption("Start point: Zürich HB")
    start = min(max(first, dt.date.today()), last)   # before the season → first day; during it → today
    day = st.date_input("Ski day", value=start, min_value=start, max_value=last)
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
cs = consumer_surplus(data, day.isoformat(), B0=B0, v=v, mode=mode, travel_pass=travel_pass,
                      level=level, weights=weights)
ranking = rank_resorts(cs, budget)

st.subheader("Ranking")
if ranking.empty:   # budget too low, or no resort open on that day
    if budget is None:
        st.info(f"No resort has a day-pass price on {day.day} {day:%B %Y}.")
    else:
        cheapest = (cs["P"] + cs["K"]).min()
        st.info(f"No resort fits your budget of CHF {budget} on {day.day} {day:%B %Y}. "
                f"Cheapest day pass + travel on that day: CHF {cheapest:.0f}.")
    st.stop()

# snow on that day (expected values, task 14) → merge on resort_id
snow_day = data.loc[data["date"] == day.isoformat(), ["resort_id", "HS_exp", "HN3_exp"]]
table = ranking.merge(snow_day, on="resort_id", how="left")
table["worth"] = table["CS"] >= 0   # CS ≥ 0 → worth the trip compared with staying home

st.caption(f"{table['worth'].sum()} of {len(table)} resorts are worth the trip (CS ≥ 0).")
st.dataframe(
    table[["rank", "resort", "CS", "worth", "B", "P", "K", "T_h", "vT", "HS_exp", "HN3_exp"]],
    hide_index=True,
    column_config={
        "rank": st.column_config.NumberColumn("#", width="small"),
        "resort": "Resort",
        "CS": st.column_config.NumberColumn("Surplus CS", format="CHF %.0f"),
        "worth": st.column_config.CheckboxColumn("Worth the trip"),
        "B": st.column_config.NumberColumn("Benefit B", format="CHF %.0f"),
        "P": st.column_config.NumberColumn("Day pass P", format="CHF %.2f"),
        "K": st.column_config.NumberColumn("Travel cost K", format="CHF %.2f"),
        "T_h": st.column_config.NumberColumn("Travel time", format="%.1f h"),
        "vT": st.column_config.NumberColumn("Time cost v·T", format="CHF %.0f"),
        "HS_exp": st.column_config.NumberColumn("Snow depth", format="%.0f cm"),
        "HN3_exp": st.column_config.NumberColumn("New snow (3 days)", format="%.0f cm"),
    },
)


# resorts missing from the table: closed on that day (no price) or above the budget
closed = cs.loc[cs["P"].isna(), "resort"].sort_values()
if len(closed) > 0:
    st.caption(f"Not open on {day.day} {day:%B %Y} ({len(closed)}): {', '.join(closed)}.")
over_budget = cs["P"].notna().sum() - len(ranking)
if over_budget > 0:
    st.caption(f"{over_budget} more open resort(s) above your budget of CHF {budget}.")

# share the top resort's snow station with the snow pages (same key as pages 1 and 2);
# only when the top resort changes, so a station picked on a snow page is not overwritten
# (task 17.6: switch to the resort picked in "Resort details")
top = ranking.iloc[0]
if st.session_state.get("finder_resort") != top["resort"]:
    st.session_state.finder_resort = top["resort"]
    st.session_state.station = data.loc[data["resort_id"] == top["resort_id"], "station_code"].iloc[0]

scraped = data["scraped_on"].dropna().max()
st.caption(f"CS = B − P − K − v·T. Price: Pricenow, scraped on {scraped}. "
           "Snow: historical values at TIT2 Titlisboden (until the snow forecast is available). "
           "Train: Zürich HB → Engelberg incl. 10 min walk; car: OpenRouteService, CHF 0.28/km + CHF 10 parking.")