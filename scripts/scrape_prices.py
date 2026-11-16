"""Scrape day-pass prices for Engelberg-Titlis (Pricenow API) and save them to data_clean/prices.csv.

Run from the repo root:  python scripts/scrape_prices.py
"""
import json
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parents[1] / "data_clean" / "prices.csv"

URL = "https://api.pricenow.dev/api/booking/products/180000/journey/validities"
HEADERS = {
    "pratiq-channel-uuid": "dbe49cb5-8c06-498a-901c-fbf65d1166e5",
    "pratiq-api-version": "2025-02-18",
    "pratiq-superjson": "true",
    "accept-language": "en",
    "content-type": "application/json",
    "Origin": "https://shop.titlis.ch",
    "Referer": "https://shop.titlis.ch/",
    "User-Agent": "SkiGuru student project (UZH, non-commercial)",
}
FORM_STATE = {
    "allocation": {"kind": "persontype",
                   "values": [{"kind": "anonymous", "quantity": 1,
                               "personType": "adult_age20to999"}]},
    "attributes": {"duration": "1d"},
}
MONTHS = [(2026, 12), (2027, 1), (2027, 2), (2027, 3), (2027, 4)]


def fetch_month(year, month):
    """Day-pass prices (CHF) for one month."""
    start = pd.Timestamp(year=year, month=month, day=1, tz="Europe/Zurich")
    end = start + pd.DateOffset(months=1) - pd.Timedelta(milliseconds=1)
    params = {
        "from": start.to_pydatetime().isoformat(timespec="milliseconds"),
        "to": end.to_pydatetime().isoformat(timespec="milliseconds"),
        "formState": json.dumps(FORM_STATE, separators=(",", ":")),
    }
    r = requests.get(URL, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    options = r.json()["json"]["data"]["options"]
    if not options:
        return pd.DataFrame(columns=["date", "price"])

    raw = pd.json_normalize(options)
    day = raw[raw["label"].str.startswith("1 Tag ") & raw["isAvailable"]].copy()
    day["date"] = pd.to_datetime(day["value.from"]).dt.tz_convert("Europe/Zurich").dt.date
    day["price"] = day["price.minPrice"] / 100
    return day[["date", "price"]]


def main():
    frames = []
    for y, m in MONTHS:
        frames.append(fetch_month(y, m))
        time.sleep(2)  # politeness: pause between requests

    new = pd.concat(frames, ignore_index=True)
    new["resort"] = "Engelberg-Titlis"
    new["scraped_on"] = date.today()
    new["days_ahead"] = (pd.to_datetime(new["date"]) - pd.to_datetime(new["scraped_on"])).dt.days
    new = new[["resort", "date", "price", "scraped_on", "days_ahead"]]

    # keep earlier scrapes (one row per resort, date and scrape day)
    if OUT.exists():
        old = pd.read_csv(OUT)
        new = pd.concat([old, new.astype({"date": str, "scraped_on": str})], ignore_index=True)
        new = new.drop_duplicates(["resort", "date", "scraped_on"], keep="last")

    new.to_csv(OUT, index=False)
    print(f"Saved {len(new)} rows to {OUT}")


if __name__ == "__main__":
    main()