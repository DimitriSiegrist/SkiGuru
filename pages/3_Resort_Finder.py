import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from src.finder import (DEFAULT_IMPORTANCE, DEFAULT_TOTAL, LEVEL_KM, benefit, consumer_surplus,
                        load_data, merge_tables, rank_resorts, scaled_attributes,
                        weights_from_importance)
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

st.caption(f"{table['worth'].sum()} of {len(table)} resorts are worth the trip (CS ≥ 0). "
           "Click a row for details.")
event = st.dataframe(
    table[["rank", "resort", "CS", "worth", "B", "P", "K", "T_h", "vT", "HS_exp", "HN3_exp"]],
    hide_index=True,
    on_select="rerun", selection_mode="single-row",
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

# --- selected resort (task 17.3): clicked row, otherwise the top-ranked resort ---
rows = event.selection.rows
sel = table.iloc[rows[0]] if rows else table.iloc[0]

# share the selected resort's snow station with the snow pages (same key as pages 1 and 2);
# only when the selected resort changes, so a station picked on a snow page is not overwritten
if st.session_state.get("finder_resort") != sel["resort"]:
    st.session_state.finder_resort = sel["resort"]
    st.session_state.station = data.loc[data["resort_id"] == sel["resort_id"], "station_code"].iloc[0]

st.subheader(f"{sel['rank']}. {sel['resort']}")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Benefit B", f"CHF {sel['B']:.0f}")
m2.metric("Day pass P", f"CHF {sel['P']:.2f}")
m3.metric("Travel cost K", f"CHF {sel['K']:.2f}")
m4.metric("Travel time", f"{sel['T_h']:.1f} h", f"CHF {sel['vT']:.0f} time cost", delta_color="off")
m5.metric("Consumer surplus", f"CHF {sel['CS']:.0f}")

if sel["worth"]:
    st.success(f"Worth the trip: you gain CHF {sel['CS']:.0f} compared with staying home.")
else:
    st.warning(f"Not worth it: the trip costs you CHF {-sel['CS']:.0f} more than it is worth to you.")


# waterfall B − P − K − v·T = CS (task 17.3): each cost bar steps down from where the previous one ended
steps = pd.DataFrame({
    "part": ["Benefit B", "Day pass P", "Travel cost K", "Time cost v·T", "Surplus CS"],
    "value": [sel["B"], -sel["P"], -sel["K"], -sel["vT"], sel["CS"]],
    "kind": ["benefit", "cost", "cost", "cost", "surplus"],
})
steps["end"] = steps["value"].cumsum()
steps.loc[4, "end"] = sel["CS"]                 # CS bar starts at 0, not at the running total
steps["start"] = steps["end"] - steps["value"]
steps["label_x"] = steps[["start", "end"]].max(axis=1)

bars = alt.Chart(steps).mark_bar(cornerRadius=4, size=22).encode(
    y=alt.Y("part:N", sort=None, title=None),
    x=alt.X("start:Q", title="CHF"),
    x2="end:Q",
    color=alt.Color("kind:N", legend=None,
                    scale=alt.Scale(domain=["benefit", "cost", "surplus"],
                                    range=["#4a4a4a", "#b5b5b5", "#111111"])),
    tooltip=[alt.Tooltip("part:N", title="Part"), alt.Tooltip("value:Q", title="CHF", format="+.0f")],
)
labels = alt.Chart(steps).mark_text(align="left", dx=6, color="#333333").encode(
    y=alt.Y("part:N", sort=None), x="label_x:Q", text=alt.Text("value:Q", format="+.0f"),
)
zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#999999").encode(x="x:Q")
st.altair_chart((bars + labels + zero).properties(height=220))


# breakdown per attribute (task 17.3): raw value → x̃ → w → w·x̃, same functions as the ranking
row = data[(data["resort_id"] == sel["resort_id"]) & (data["date"] == day.isoformat())]
x = scaled_attributes(row, level)
_, contrib = benefit(x, weights, B0)
r = row.iloc[0]
colour = {"beginner": "blue", "intermediate": "red", "expert": "black"}[level]


def stars(v):
    return "no test report (neutral)" if pd.isna(v) else f"{int(v)} of 5 stars"


raw = {"piste_km": f"{r['piste_km']:.0f} km", "vertical_drop": f"{r['vertical_drop']:.0f} m",
       "top_alt": f"{r['top_alt']:.0f} m", "snowmaking_share": f"{r['snowmaking_share']:.0%} of pistes",
       "difficulty": f"{r[LEVEL_KM[level]] / r['piste_km']:.0%} {colour} km",
       "x_snow_depth": f"{r['HS_exp']:.0f} cm", "x_new_snow": f"{r['HN3_exp']:.0f} cm in 3 days",
       "rating_family": stars(r["rating_family"]), "rating_freeride": stars(r["rating_freeride"]),
       "rating_park": stars(r["rating_park"])}
calc = pd.DataFrame({
    "Attribute": [LABELS[k] for k in LABELS],
    "Value": [raw[k] for k in LABELS],
    "x̃": [x[k].iloc[0] for k in LABELS],
    "w": [weights[k] for k in LABELS],
    "w·x̃": [contrib[k].iloc[0] for k in LABELS],
})

with st.expander("How is the CS calculated?"):
    st.dataframe(calc, hide_index=True, column_config={
        "x̃": st.column_config.NumberColumn("Scaled x̃ (0–1)", format="%.2f"),
        "w": st.column_config.NumberColumn("Weight w", format="CHF %.2f"),
        "w·x̃": st.column_config.NumberColumn("Contribution w·x̃", format="CHF %.2f"),
    })
    st.markdown(f"Sum of contributions CHF {contrib.iloc[0].sum():.2f} + B₀ CHF {B0} "
                f"= **B = CHF {sel['B']:.2f}**")
    st.markdown(f"B − P − K − v·T = {sel['B']:.2f} − {sel['P']:.2f} − {sel['K']:.2f} − {sel['vT']:.2f} "
                f"= **CS = CHF {sel['CS']:.2f}**")

scraped = data["scraped_on"].dropna().max()
st.caption(f"CS = B − P − K − v·T. Price: Pricenow, scraped on {scraped}. "
           "Snow: historical values at TIT2 Titlisboden (until the snow forecast is available). "
           "Train: Zürich HB → Engelberg incl. 10 min walk; car: OpenRouteService, CHF 0.28/km + CHF 10 parking.")