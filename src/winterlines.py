"""Winter lines for the home page.

One hairline per winter of snow depth at a single station, oldest winter at the back.
The drawing is plain SVG built as a string, the movement is CSS only (no JavaScript).
"""

import base64

import numpy as np
import pandas as pd
import streamlit as st

from src.data import STATIONS, load_snow
from src.style import ASSETS

STATION = "WFJ2"   # Weissfluhjoch, the longest series in our data

# Geometry of the drawing in SVG units. The drawing scales with the page width.
WIDTH = 1180       # total width
RIGHT = 64         # room on the right for the year labels
PLOT = WIDTH - RIGHT
DAYS = 304         # 1 October to 31 July
SCALE = 0.42       # SVG units per cm of snow
STEP = 7.5         # vertical distance between two winters
TOP = 156          # baseline of the oldest winter
MONTHS = [
    ("Oct", 0), ("Nov", 31), ("Dec", 61), ("Jan", 92), ("Feb", 123),
    ("Mar", 151), ("Apr", 182), ("May", 212), ("Jun", 243), ("Jul", 273),
]

DRAWING_CSS = """
.ridge { display: block; width: 100%; height: auto; overflow: visible; }
.ridge .occ { fill: #ffffff; }
.ridge .ln {
    fill: none; stroke: #111111; stroke-width: 1; stroke-linejoin: round;
    stroke-dasharray: var(--len); stroke-dashoffset: var(--len);
    animation: ridge-draw 1.5s cubic-bezier(.45, 0, .2, 1) forwards;
}
.ridge .ln.now { stroke-width: 2; animation-duration: .7s; animation-delay: 2s !important; }
.ridge .occ:hover + .ln { stroke: #111111 !important; stroke-width: 2.2; }
.ridge text { font-size: 10.5px; fill: #8c8c8c; }
.ridge text.month { letter-spacing: .14em; text-transform: uppercase; font-size: 9.5px; }
.ridge text.today { fill: #111111; font-size: 12px; }
.ridge text.read { opacity: 0; fill: #111111; font-size: 12px; text-anchor: end; transition: opacity .15s; }
.ridge .occ:hover + .ln + text.read { opacity: 1; }
.ridge line.tick, .ridge line.bar { stroke: #111111; stroke-width: 1; }
.ridge .late { opacity: 0; animation: ridge-fade .7s ease-out 2.6s forwards; }
@keyframes ridge-draw { to { stroke-dashoffset: 0; } }
@keyframes ridge-fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) {
    .ridge .ln { animation: none; stroke-dashoffset: 0; }
    .ridge .late { animation: none; opacity: 1; }
}
"""


def format_metres(value):
    """2536.0 -> 2'536"""
    return f"{value:,.0f}".replace(",", "'")


def winter_label(hyear):
    """1993 -> 1992/93"""
    return f"{hyear - 1}/{str(hyear)[-2:]}"


@st.cache_data(ttl=1800, show_spinner=False)
def load_winters(station=STATION):
    """Snow depth per winter (1 October to 31 July) at one station.

    Returns a dict, or None if the station has no data:
      seasons    {hyear: array of daily snow depth in cm, gaps filled, 5-day mean}
      peaks      {hyear: highest measured snow depth in cm}
      latest     date of the last measurement
      hs_now     snow depth of the last measurement
      running    True while the newest winter is still going on
      name, elevation   of the station
    """
    data, _ = load_snow()
    one = data[data["station_code"] == station].dropna(subset=["HS"]).sort_values("date")
    if one.empty:
        return None

    seasons, peaks = {}, {}
    for hyear, part in one.groupby("hyear"):
        hyear = int(hyear)
        start = pd.Timestamp(year=hyear - 1, month=10, day=1)
        stop = pd.Timestamp(year=hyear, month=7, day=31)
        part = part[(part["date"] >= start) & (part["date"] <= stop)].drop_duplicates("date")
        if part.empty:
            continue
        days = pd.date_range(start, min(stop, part["date"].max()))
        series = part.set_index("date")["HS"].astype("float64").reindex(days)
        series = series.interpolate(limit_direction="both").rolling(5, center=True, min_periods=1).mean()
        seasons[hyear] = series.to_numpy()
        peaks[hyear] = float(part["HS"].max())

    if not seasons:
        return None

    last = one.iloc[-1]
    newest = max(seasons)
    running = last["date"] <= pd.Timestamp(year=newest, month=7, day=31) and len(seasons) > 1

    stations = pd.read_csv(STATIONS)
    row = stations[stations["station_code"] == station]
    return {
        "seasons": seasons,
        "peaks": peaks,
        "latest": last["date"],
        "hs_now": float(last["HS"]),
        "running": bool(running),
        "name": row.iloc[0]["name"] if not row.empty else station,
        "elevation": float(row.iloc[0]["elevation"]) if not row.empty else None,
    }


def _icon_uri(name):
    """The icon as a data URI, so it can sit inside the SVG."""
    return "data:image/png;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


def _points(values, every=1):
    """Daily values -> x/y in SVG units, relative to a baseline at y = 0."""
    xs = np.arange(len(values))[::every] / DAYS * PLOT
    ys = -values[::every] * SCALE
    return xs, ys


def ridgeline_svg(winters):
    """The drawing as one SVG string. Put it on the page with st.markdown(..., unsafe_allow_html=True)."""
    seasons, peaks = winters["seasons"], winters["peaks"]
    years = sorted(seasons)
    complete = years[:-1] if winters["running"] else years
    out = []

    # --- finished winters: white area (hides the lines behind) plus the line itself ---
    for i, year in enumerate(complete):
        base = TOP + i * STEP
        xs, ys = _points(seasons[year], every=2)
        ys = ys + base
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        length = float(np.hypot(np.diff(xs), np.diff(ys)).sum())
        age = i / max(len(complete) - 1, 1)
        tone = round(168 - (168 - 17) * age ** 1.6)          # older winters are lighter
        out.append(f'<polygon class="occ" points="0,{base} {points} {xs[-1]:.1f},{base}"></polygon>')
        out.append(
            f'<polyline class="ln" points="{points}" '
            f'style="--len:{length:.0f};animation-delay:{i * 45}ms;stroke:rgb({tone},{tone},{tone})"></polyline>'
        )
        out.append(
            f'<text class="read" x="{WIDTH}" y="READ_Y">Winter {winter_label(year)}: up to {peaks[year]:.0f} cm</text>'
        )
        if i == 0 or year % 10 == 0 or year == complete[-1]:
            out.append(f'<text x="{PLOT + 10}" y="{base + 3.5}">{winter_label(year)}</text>')

    # --- the winter that is still running: a short line in front, the skier stands at today ---
    base = TOP + (len(complete) - 1) * STEP + 46
    if winters["running"]:
        values = seasons[years[-1]]
        xs, ys = _points(values)
        ys = ys + base
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        length = float(np.hypot(np.diff(xs), np.diff(ys)).sum()) if len(xs) > 1 else 0
        tip_x, tip_y = xs[-1], ys[-1]
        latest = winters["latest"]
        remark = "This winter has just begun." if len(values) <= 61 else "This winter so far."
        flip = tip_x > PLOT - 260                              # late in the season the text moves left of the skier
        text_x = tip_x - 22 if flip else tip_x + 40
        anchor = ' style="text-anchor:end"' if flip else ""
        out.append(f'<polyline class="ln now" points="{points}" style="--len:{length:.0f}"></polyline>')
        out.append(
            '<g class="late">'
            f'<image href="{_icon_uri("ski_touring.png")}" x="{tip_x - 14:.1f}" y="{tip_y - 43:.1f}" width="46" height="46"></image>'
            f'<text class="today" x="{text_x:.1f}" y="{tip_y - 17:.1f}"{anchor}>'
            f'{latest.day} {latest:%B %Y}: {winters["hs_now"]:.0f} cm</text>'
            f'<text x="{text_x:.1f}" y="{tip_y - 3:.1f}"{anchor}>{remark}</text>'
            "</g>"
        )

    # --- month scale ---
    axis = base + 16
    for name, day in MONTHS:
        x = day / DAYS * PLOT
        out.append(f'<line class="tick" x1="{x:.1f}" y1="{axis}" x2="{x:.1f}" y2="{axis + 5}"></line>')
        out.append(f'<text class="month" x="{x + 6:.1f}" y="{axis + 6}">{name}</text>')

    # --- scale bar: 100 cm of snow ---
    bar_x = PLOT - 4
    out.append(f'<line class="bar" x1="{bar_x}" y1="{base - 100 * SCALE:.1f}" x2="{bar_x}" y2="{base}"></line>')
    out.append(
        f'<text x="{bar_x - 7}" y="{base - 100 * SCALE / 2 + 3.5:.1f}" style="text-anchor:end">100 cm of snow</text>'
    )

    height = axis + 14
    body = "".join(out).replace("READ_Y", f"{axis + 6}")
    first = winter_label(years[0])
    return (
        f'<svg class="ridge" viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-label="Snow depth on {winters["name"]}, one line per winter since {first}">{body}</svg>'
    )