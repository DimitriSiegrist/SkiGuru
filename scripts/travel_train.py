"""Train travel time (transport.opendata.ch) and fares (docs/train_fares.csv) from Zurich HB
to each resort → data_clean/travel_train.csv

Run from the repo root:  python scripts/travel_train.py
"""
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
FARES = ROOT / "docs" / "train_fares.csv"
OUT = ROOT / "data_clean" / "travel_train.csv"

URL = "https://transport.opendata.ch/v1/connections"
START = "Zürich HB"
REF_DATE = "2026-12-10"            # typical weekday in the season
TIME_OUT, TIME_BACK = "07:00", "16:30"


def parse_duration(s):
    """'00d01:43:00' → 103 (minutes)"""
    days, hms = s.split("d")
    h, m, _ = map(int, hms.split(":"))
    return int(days) * 24 * 60 + h * 60 + m


def train_minutes(frm, to, date_, time_):
    """Shortest of the next 4 connections, in minutes."""
    params = {"from": frm, "to": to, "date": date_, "time": time_, "limit": 4}
    r = requests.get(URL, params=params, timeout=20)
    r.raise_for_status()
    return min(parse_duration(c["duration"]) for c in r.json()["connections"])


def main():
    fares = pd.read_csv(FARES)
    rows = []
    failed = []
    for _, f in fares.iterrows():
        try:
            t_out = train_minutes(START, f["to_station"], REF_DATE, TIME_OUT)
            time.sleep(1)
            t_back = train_minutes(f["to_station"], START, REF_DATE, TIME_BACK)
            time.sleep(1)
        except Exception as e:  # unknown stop, no connection, timeout
            print(f"FAILED {f['resort']} ({f['to_station']}): {e}")
            failed.append(f["resort"])
            continue
        walk = int(f["last_mile_min"])   # station → valley station, each way (docs/train_fares.csv)
        rows.append({
            "resort": f["resort"],
            "start": START,
            "t_out_min": t_out,
            "t_back_min": t_back,
            "last_mile_min": walk,
            "t_round_min": t_out + t_back + 2 * walk,
            "fare_full_return": f["fare_full_return"],
            "fare_halbtax_return": f["fare_halbtax_return"],
            "queried_on": date.today(),
        })
        print(f"ok {f['resort']}: {t_out} + {t_back} min")
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(out)
    print(f"Saved {len(out)} rows to {OUT}")
    if failed:
        print(f"{len(failed)} failed: {failed}")
    print(f"Saved {len(out)} rows to {OUT}")


if __name__ == "__main__":
    main()