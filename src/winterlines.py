"""Winter lines for the home page.

One hairline per winter of snow depth at one station, oldest winter at the back. The winter that is
still running is the bold line in front: the skier walks along it up to today.
The drawing is plain SVG built as a string, the movement is CSS only (no JavaScript).
"""

import base64

import numpy as np
import pandas as pd
import streamlit as st

from src.data import load_snow, load_stations
from src.style import ASSETS

STATION = "WFJ2"       # Weissfluhjoch, the station shown first
MIN_WINTERS = 20       # stations with fewer finished winters are not offered
MIN_DAYS = 258         # a finished winter needs measurements on 85 % of its days

# Geometry of the drawing in SVG units. The drawing scales with the page width.
WIDTH = 1180           # total width
RIGHT = 64             # room on the right for the year labels
PLOT = WIDTH - RIGHT
DAYS = 304             # 1 October to 31 July, without 29 February
TOP = 156              # baseline of the oldest winter
STACK = 247.5          # from the baseline of the oldest winter down to the latest finished one
GAP = 46               # from there down to the winter that is still running
SCALE = 0.42           # SVG units per cm of snow ...
PEAK = 147             # ... but less where needed, so that the deepest snow is never drawn higher than this
START = 2.0            # seconds after loading at which the skier sets off
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
}
.ridge .ln.now { stroke-width: 2; stroke-linecap: round; }
.ridge text { font-size: 10.5px; fill: #8c8c8c; }
.ridge text.month { letter-spacing: .14em; text-transform: uppercase; font-size: 9.5px; }
.ridge line.tick, .ridge line.bar { stroke: #111111; stroke-width: 1; }

/* point at a winter: its line and its year turn bold, its numbers appear at the bottom right */
.ridge .row:hover .ln { stroke: #111111 !important; stroke-width: 2.2 !important; }
.ridge text.read { opacity: 0; fill: #111111; font-size: 12px; text-anchor: end; transition: opacity .15s; pointer-events: none; }
.ridge .row:hover text.read { opacity: 1; }
.ridge .row:hover text.year { fill: #111111; }

/* the running winter: the skier and what is written next to it */
.ridge .walker { opacity: 0; }
.ridge .late { opacity: 0; animation: ridge-fade .7s ease-out forwards; }
.ridge .late text { stroke: #ffffff; stroke-width: 6px; paint-order: stroke fill; stroke-linejoin: round; cursor: default; }
.ridge text.today { fill: #111111; font-size: 12px; }

@keyframes ridge-draw { to { stroke-dashoffset: 0; } }
@keyframes ridge-fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes ridge-show { to { opacity: 1; } }
@keyframes ridge-step { from { transform: translateY(0); } to { transform: translateY(-2.2px); } }
@media (prefers-reduced-motion: reduce) {
    .ridge * { animation: none !important; }
    .ridge .ln { stroke-dashoffset: 0; }
    .ridge .late, .ridge .walker { opacity: 1; }
}
"""


def format_metres(value):
    """2536.0 -> 2'536"""
    return f"{value:,.0f}".replace(",", "'")


def winter_label(hyear):
    """1993 -> 1992/93"""
    return f"{hyear - 1}/{str(hyear)[-2:]}"


def _today():
    return pd.Timestamp.today().normalize()


@st.cache_data(ttl=1800, show_spinner=False)
def station_choices():
    """The stations that can be shown, as {station_code: "Weissfluhjoch, 2'536 m"}, sorted by name.

    A station is offered if it measures at the moment and has at least MIN_WINTERS finished winters.
    """
    data, _ = load_snow()
    data = data.dropna(subset=["HS"])
    data = data[~data["date"].dt.month.isin([8, 9])]                       # a winter runs from October to July
    days = data.groupby(["station_code", "hyear"])["HS"].count().reset_index(name="days")
    over = pd.to_datetime(days["hyear"].astype(str) + "-07-31") < _today()
    winters = days[over & (days["days"] >= MIN_DAYS)].groupby("station_code").size()

    stations = load_stations()                                             # the snow stations that measure at the moment
    stations = stations[stations["station_code"].map(winters).fillna(0) >= MIN_WINTERS].sort_values("name")
    return {
        code: f"{name}, {format_metres(elevation)} m" if pd.notna(elevation) else name
        for code, name, elevation in zip(stations["station_code"], stations["name"], stations["elevation"])
    }


@st.cache_data(ttl=1800, show_spinner=False)
def load_winters(station=STATION):
    """Snow depth per winter (1 October to 31 July) at one station.

    Returns a dict, or None if the station has no data:
      seasons    {hyear: daily snow depth in cm, gaps filled, 5-day mean}    for the lines
      measured   {hyear: daily snow depth in cm, gaps filled}                for the numbers
      peaks      {hyear: highest measured snow depth in cm}
      latest     date of the last measurement
      hs_now     snow depth of the last measurement
      running    True while the newest winter is still going on
    29 February is left out, so the same position means the same date in every winter.
    """
    data, _ = load_snow()
    one = data[data["station_code"] == station].dropna(subset=["HS"])
    one = one.sort_values("date").drop_duplicates("date")
    if one.empty:
        return None

    seasons, measured, peaks = {}, {}, {}
    running = False
    for hyear, part in one.groupby("hyear"):
        hyear = int(hyear)
        start = pd.Timestamp(year=hyear - 1, month=10, day=1)
        stop = pd.Timestamp(year=hyear, month=7, day=31)
        part = part[(part["date"] >= start) & (part["date"] <= stop)]
        if part.empty:
            continue
        over = _today() > stop
        if over and len(part) < MIN_DAYS:
            continue                                                       # too many gaps to draw this winter
        days = pd.date_range(start, stop if over else part["date"].max())
        filled = part.set_index("date")["HS"].astype("float64").reindex(days).interpolate(limit_direction="both")
        smooth = filled.rolling(5, center=True, min_periods=1).mean()
        keep = ~((days.month == 2) & (days.day == 29))
        seasons[hyear] = smooth[keep].to_numpy()
        measured[hyear] = filled[keep].to_numpy()
        peaks[hyear] = float(part["HS"].max())
        running = not over                                                 # the newest winter decides

    if not seasons:
        return None

    last = one.iloc[-1]
    return {
        "seasons": seasons,
        "measured": measured,
        "peaks": peaks,
        "latest": last["date"],
        "hs_now": float(last["HS"]),
        "running": running,
    }


def _icon_uri(name):
    """The icon as a data URI, so it can sit inside the SVG."""
    return "data:image/png;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


def _points(values, scale, every=1):
    """Daily values -> x/y in SVG units, relative to a baseline at y = 0."""
    xs = np.arange(len(values))[::every] / DAYS * PLOT
    ys = -values[::every] * scale
    return xs, ys


def _length(xs, ys):
    """Length of a line through these points."""
    return float(np.hypot(np.diff(xs), np.diff(ys)).sum())


def _standing(then, hs_now):
    """One sentence on how today's snow depth compares with the same day in the finished winters."""
    less = sum(1 for value in then.values() if value < hs_now)
    if less == 0:
        return "No winter had less snow on this day."
    if less == len(then):
        return f"All {less} winters had less snow on this day."
    return f"{less} of {len(then)} winters had less snow on this day."


def _walk(xs, ys, stops=60):
    """CSS keyframes that move the skier along the line at an even pace."""
    walked = np.concatenate([[0], np.cumsum(np.hypot(np.diff(xs), np.diff(ys)))])    # distance covered at each point
    frames = []
    for k in range(stops + 1):
        at = walked[-1] * k / stops
        x, y = np.interp(at, walked, xs), np.interp(at, walked, ys)
        frames.append(f"{100 * k / stops:.1f}% {{ transform: translate({x:.1f}px, {y:.1f}px); }}")
    return "@keyframes ridge-walk { " + " ".join(frames) + " }"


def winter_lines_svg(winters, name=""):
    """The drawing as one string. Put it on the page with st.markdown(..., unsafe_allow_html=True)."""
    seasons, measured, peaks = winters["seasons"], winters["measured"], winters["peaks"]
    years = sorted(seasons)
    current = years[-1] if winters["running"] else None
    finished = [year for year in years if year != current]
    if not finished:
        return ""

    count = len(finished)
    step = STACK / max(count - 1, 1)                                       # vertical distance between two winters
    deepest = max(float(seasons[year].max()) for year in years)
    scale = min(SCALE, PEAK / deepest) if deepest > 0 else SCALE
    base_now = TOP + STACK + GAP                                           # baseline of the running winter
    axis = base_now + 16
    out, keyframes = [], ""

    # --- today: how much snow lies now, and how much lay on this day in the finished winters? ---
    then = {}
    if current:
        hs_now, latest = winters["hs_now"], winters["latest"]
        day_now = len(seasons[current]) - 1
        then = {year: float(measured[year][day_now]) for year in finished}
        xs, ys = _points(np.append(seasons[current][:-1], hs_now), scale)  # the line ends at today's measurement
        ys = ys + base_now
        tip_x, tip_y = float(xs[-1]), float(ys[-1])
        walk = round(0.9 + 2.6 * day_now / DAYS, 2)                        # seconds the skier needs
        arrive = START + walk

    # --- finished winters: white area (hides the lines behind), the line, the year ---
    size = min(10.5, step + 0.5)                                           # the years must fit between two lines
    for i, year in enumerate(finished):
        base = TOP + i * step
        xs_i, ys_i = _points(seasons[year], scale, every=2)
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs_i, ys_i))
        tone = round(168 - (168 - 17) * (i / max(count - 1, 1)) ** 1.6)    # older winters are lighter
        row = [
            f'<polygon class="occ" points="0,0 {points} {xs_i[-1]:.1f},0"></polygon>',
            f'<polyline class="ln" points="{points}" style="--len:{_length(xs_i, ys_i):.0f};stroke:rgb({tone},{tone},{tone});'
            f'animation:ridge-draw 1.5s cubic-bezier(.45,0,.2,1) {i * 45}ms forwards"></polyline>',
        ]

        read = f"Winter {winter_label(year)}: up to {peaks[year]:.0f} cm"
        if current:
            read += f", {then[year]:.0f} cm on {latest.day} {latest:%B}"
        row.append(f'<text class="read" x="{WIDTH}" y="{axis + 22 - base:.1f}">{read}</text>')
        row.append(f'<text class="year" x="{PLOT + 10}" y="{size * 0.35:.1f}" style="font-size:{size}px">{winter_label(year)}</text>')
        out.append(f'<g class="row" transform="translate(0,{base:.1f})">{"".join(row)}</g>')

    # --- the winter that is still running: the line draws itself and the skier walks along it ---
    if current:
        keyframes = _walk(xs, ys)
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        steps = max(2, round(walk / 0.34 / 2) * 2)                         # the skier bobs a little with every step
        out.append(
            f'<polyline class="ln now" points="{points}" '
            f'style="--len:{_length(xs, ys) + 1:.0f};animation:ridge-draw {walk}s linear {START}s forwards"></polyline>'
        )
        out.append(
            f'<g class="walker" style="transform:translate({tip_x:.1f}px,{tip_y:.1f}px);'
            f'animation:ridge-walk {walk}s linear {START}s both,ridge-show .3s ease-out {START - 0.3}s forwards">'
            f'<image href="{_icon_uri("ski_touring.png")}" x="-14" y="-43" width="46" height="46" '
            f'style="animation:ridge-step {walk / steps:.3f}s ease-in-out {START}s {steps} alternate"></image></g>'
        )

        flip = tip_x > PLOT - 260                                          # late in the season the text moves left of the skier
        text_x = tip_x - 22 if flip else tip_x + 40
        anchor = ' style="text-anchor:end"' if flip else ""
        out.append(
            f'<g class="late" style="animation-delay:{arrive + 0.1:.2f}s">'
            f'<text class="today" x="{text_x:.1f}" y="{tip_y - 17:.1f}"{anchor}>{latest.day} {latest:%B %Y}: {hs_now:.0f} cm</text>'
            f'<text x="{text_x:.1f}" y="{tip_y - 3:.1f}"{anchor}>{_standing(then, hs_now)}</text>'
            "</g>"
        )

    # --- month scale ---
    for month, day in MONTHS:
        x = day / DAYS * PLOT
        out.append(f'<line class="tick" x1="{x:.1f}" y1="{axis}" x2="{x:.1f}" y2="{axis + 5}"></line>')
        out.append(f'<text class="month" x="{x + 6:.1f}" y="{axis + 6}">{month}</text>')

    # --- scale bar: 100 cm of snow, below the years ---
    bar_x, middle = PLOT + 12, base_now - 100 * scale / 2
    out.append(f'<line class="bar" x1="{bar_x}" y1="{base_now - 100 * scale:.1f}" x2="{bar_x}" y2="{base_now}"></line>')
    out.append(f'<text x="{bar_x + 7}" y="{middle - 2:.1f}">100 cm</text>')
    out.append(f'<text x="{bar_x + 7}" y="{middle + 10:.1f}">of snow</text>')

    label = f"Snow depth on {name}, one line per winter since {winter_label(years[0])}"
    return (
        f"<style>{keyframes}</style>"
        f'<svg class="ridge" viewBox="0 0 {WIDTH} {axis + 30}" role="img" aria-label="{label}">{"".join(out)}</svg>'
    )