"""Scrape day-pass prices for Engelberg-Titlis (Pricenow API) and save them to data_clean/prices.csv.

Run from the repo root:  python scripts/scrape_prices.py
"""
import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_clean" / "prices.csv"

USER_AGENT = "SkiGuru student project (UZH, non-commercial)"

# one entry per resort: which parser to use and its parameters (task 11.1)
RESORTS = {
    "engelberg_titlis": {
        "parser": "pricenow",
        "product": 180000,
        "channel_uuid": "dbe49cb5-8c06-498a-901c-fbf65d1166e5",
        "shop": "https://shop.titlis.ch",
        "person_type": "adult_age20to999",
        "label_prefix": "1 Tag ",
    },
    "flims_laax_falera": {
        "parser": "pricenow",
        "product": 1190144,
        "channel_uuid": "e3570742-351d-420b-8f86-ab31a1363e10",
        "shop": "https://shop.laax.com",
        "person_type": "adult",
        "label_prefix": "2026/27",
    },
    "toggenburg_chaeserrugg": {
        "parser": "pricenow",
        "product": 110000,
        "channel_uuid": "57a22950-c9ed-4a1d-b7e9-a18edccc65a5",
        "shop": "https://shop.chaeserrugg.ch",
        "person_type": "adult",
        "label_prefix": "4h & 1d Ski Ticket",
    },
    "adelboden_lenk": {
        "parser": "adelboden",
        "url": "https://www.adelboden-lenk.ch/en/shop/json/ticket/dates/51393/4344",
        "ticket_id": 123,
        "price_group": "4180",  # adult (defaultPriceGroup)
    },
    "verbier_4_vallees": {
        "parser": "verbier",
        "url": "https://verbier4vallees.ch/en/shop/ticket/json/pricing",
        "ticket_id": 159334,
        "sector": 159527,
        "product": "0153468",      # 1 day 4Vallées
        "price_group": "0389176",  # Adult (1950-2001)
    },
    "grimentz_zinal": {
        "parser": "grimentz",
        "url": "https://grimentzinal.rma.ch/proxy/call/simulationResolver",
        "shop": "https://grimentzinal.rma.ch/en/",
        "validity": "1DAY",
        "ctid": 234,
        "product": "ANNIVIERS",  # 1 jour Val d'Anniviers
        "consumer": "ADULT",
        "season_start": "2026-12-18",  # API also prices closed days → drop days before opening
        "jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjbGllbnRJZCI6MzY5LCJhY3Rpb25zIjp7InNpbXVsYXRpb25SZXNvbHZlciI6eyJjb250cm9sbGVyIjoiUmVkcGlsbEJ1bmRsZTpBcGlcXFYyXFxTaW11bGF0aW9uOmdldFNpbXVsYXRpb25XaXRoUmVzb2x2ZXIiLCJyZXNvdXJjZSI6IlNpbXVsYXRpb24ifSwib2ZmZXJzU2VhcmNoIjp7ImNvbnRyb2xsZXIiOiJSZWRwaWxsQnVuZGxlOkFwaVxcVjJcXE9mZmVyczpzZWFyY2giLCJyZXNvdXJjZSI6Ik9mZmVycyJ9LCJwcm9kdWN0cyI6eyJjb250cm9sbGVyIjoiUmVkcGlsbEJ1bmRsZTpBcGlcXFYyXFxQcm9kdWN0OmNnZXQiLCJyZXNvdXJjZSI6IlByb2R1Y3QifX19.eeVxzUXDrgvhFDKrHfe7yT8J9bbjVbky0wKl5t0Rmy4",
    },
    "zermatt_matterhorn_ski_paradise": {
        "parser": "zermatt",
        "url": "https://www.matterhornparadise.ch/de/shop/ticket/pricing",
        "shop": "https://www.matterhornparadise.ch/de/buchen/tickets/skipass-winter",
        "ticket_id": 1501805,     # 1 Tag Skipass Zermatt
        "upgrade": 520187,        # International (+ Breuil-Cervinia/Valtournenche), matches the attributes
        "price_group": "502338",  # Erwachsen (adult)
    },
    "crans_montana": {
        "parser": "peaksolution",
        "shop": "https://shop.mycma.ch",
        "region": "sdskicm_winter_jours",
        "variant_name": "Skipass CMA 1 Day Adult",
    },
    "aletsch_arena": {
        "parser": "peaksolution",
        "shop": "https://shop.aletscharena.ch",
        "region": "aletsch-arena",
        "variant_name": "Skipass Aletsch-Arena 1 Tag Erwachsener",  # not "Adult_lsb" (other tariff, CHF 59)
    },
    "belalp": {
        "parser": "peaksolution",
        "shop": "https://shop.belalp.ch",
        "region": "Belalp",
        "variant_name": "Skipass Blatten - Belalp 1 Tag Erwachsener",
    },
}
MONTHS = [(2026, 12), (2027, 1), (2027, 2), (2027, 3), (2027, 4)]


def fetch_pricenow_month(cfg, year, month):
    """Day-pass prices (CHF) for one month from the Pricenow calendar endpoint."""
    url = f"https://api.pricenow.dev/api/booking/products/{cfg['product']}/journey/validities"
    headers = {
        "pratiq-channel-uuid": cfg["channel_uuid"],
        "pratiq-api-version": "2025-02-18",
        "pratiq-superjson": "true",
        "accept-language": "en",
        "content-type": "application/json",
        "Origin": cfg["shop"],
        "Referer": cfg["shop"] + "/",
        "User-Agent": USER_AGENT,
    }
    form_state = {
        "allocation": {"kind": "persontype",
                       "values": [{"kind": "anonymous", "quantity": 1,
                                   "personType": cfg["person_type"]}]},
        "attributes": {"duration": "1d"},
    }
    start = pd.Timestamp(year=year, month=month, day=1, tz="Europe/Zurich")
    end = start + pd.DateOffset(months=1) - pd.Timedelta(milliseconds=1)
    params = {
        "from": start.to_pydatetime().isoformat(timespec="milliseconds"),
        "to": end.to_pydatetime().isoformat(timespec="milliseconds"),
        "formState": json.dumps(form_state, separators=(",", ":")),
    }
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    options = r.json()["json"]["data"]["options"]
    if not options:
        return pd.DataFrame(columns=["date", "price"])

    raw = pd.json_normalize(options)
    day = raw[raw["label"].str.startswith(cfg["label_prefix"]) & raw["isAvailable"]].copy()
    day["date"] = pd.to_datetime(day["value.from"]).dt.tz_convert("Europe/Zurich").dt.date
    day["price"] = day["price.minPrice"] / 100  # Rappen → CHF
    return day[["date", "price"]]


def scrape_pricenow(cfg):
    """All months of the season for one Pricenow resort."""
    frames = []
    for y, m in MONTHS:
        frames.append(fetch_pricenow_month(cfg, y, m))
        time.sleep(2)  # politeness: pause between requests
    return pd.concat(frames, ignore_index=True)


# ---------- parser 2: Adelboden-Lenk (own API, monthly calendar) ----------

def fetch_adelboden_month(cfg, year, month):
    """Day-pass prices (CHF) for one month from the Adelboden-Lenk shop calendar."""
    params = {"ticketId": cfg["ticket_id"], "year": year, "month": month}
    r = requests.get(cfg["url"], headers={"User-Agent": USER_AGENT}, params=params, timeout=20)
    r.raise_for_status()
    dates = r.json()["calendarConfiguration"]["calendar"]["dates"]

    rows = []
    for d in dates:
        if d["disabled"]:  # closed day or outside the season
            continue
        rows.append({"date": d["date"][:10],  # "2026-12-13T00:00:00" → "2026-12-13"
                     "price": d["priceByPriceGroup"][cfg["price_group"]]["price"]})
    df = pd.DataFrame(rows, columns=["date", "price"])

    # the calendar also shows days of the neighbouring months → keep only this month
    return df[pd.to_datetime(df["date"]).dt.month == month]


def scrape_adelboden(cfg):
    """All months of the season for Adelboden-Lenk."""
    frames = []
    for y, m in MONTHS:
        frames.append(fetch_adelboden_month(cfg, y, m))
        time.sleep(2)  # politeness: pause between requests
    return pd.concat(frames, ignore_index=True)


# ---------- parser 3: Verbier/4 Vallées (own API, one request per day) ----------

def fetch_verbier_day(cfg, day):
    """Adult online price (CHF) for one day; None if no ticket is sold that day."""
    params = {"ticket_id": cfg["ticket_id"], "startDate": day,
              "vipPasses": "", "sector": cfg["sector"]}
    r = requests.get(cfg["url"], headers={"User-Agent": USER_AGENT}, params=params, timeout=20)
    r.raise_for_status()

    for product in r.json()["productChoices"]:  # empty list = closed day
        if product["id"] == cfg["product"]:
            for group in product["priceGroups"]:
                if group["id"] == cfg["price_group"]:
                    return group["price"]  # online price (basePrice − 10 %)
    return None


def scrape_verbier(cfg):
    """All days of the season for Verbier/4 Vallées."""
    first = pd.Timestamp(year=MONTHS[0][0], month=MONTHS[0][1], day=1)
    last = pd.Timestamp(year=MONTHS[-1][0], month=MONTHS[-1][1], day=1) + pd.offsets.MonthEnd(0)

    rows = []
    for day in pd.date_range(first, last).strftime("%Y-%m-%d"):
        price = fetch_verbier_day(cfg, day)
        if price is not None:
            rows.append({"date": day, "price": price})
        time.sleep(1)  # politeness: ~150 requests → about 3 minutes
    return pd.DataFrame(rows, columns=["date", "price"])


# ---------- parser 4: Grimentz-Zinal (own API, rma.ch, one request per day) ----------

def fetch_grimentz_day(cfg, day):
    """Adult price (CHF) for one day; None if no ticket is sold that day."""
    params = {"vc": cfg["validity"], "s": day, "ctid": cfg["ctid"],
              "pc": cfg["product"], "sk[0][cc]": cfg["consumer"]}
    headers = {"accept": "application/json;version=v2",
               "jwt": cfg["jwt"],  # public shop token (no expiry), sent by the shop with every request
               "referer": cfg["shop"],
               "User-Agent": USER_AGENT}
    r = requests.get(cfg["url"], headers=headers, params=params, timeout=20)
    if r.status_code != 200:  # closed day or outside the season → error page
        return None
    total = r.json().get("total")
    return total / 100 if total else None  # Rappen → CHF


def scrape_grimentz(cfg):
    """All days of the season for Grimentz-Zinal."""
    first = pd.Timestamp(year=MONTHS[0][0], month=MONTHS[0][1], day=1)
    last = pd.Timestamp(year=MONTHS[-1][0], month=MONTHS[-1][1], day=1) + pd.offsets.MonthEnd(0)

    rows = []
    for day in pd.date_range(first, last).strftime("%Y-%m-%d"):
        price = fetch_grimentz_day(cfg, day)
        if price is not None:
            rows.append({"date": day, "price": price})
        time.sleep(1)  # politeness: ~150 requests → about 3 minutes
    return pd.DataFrame(rows, columns=["date", "price"])


# ---------- parser 5: Zermatt (own API, one request per day, International upgrade) ----------

def fetch_zermatt_day(session, cfg, day):
    """Adult price (CHF) for one day, International pass without extra insurance; None if not sold."""
    params = {"ticketId": cfg["ticket_id"], "selectedDateStart": f"{day}T00:00:00"}
    r = session.get(cfg["url"], params=params, timeout=20)
    if r.status_code != 200:
        return None

    for conf in r.json().get("priceConfigurations", []):
        if conf["upgradeCatalog"] == cfg["upgrade"] and conf["insurance"] == "no_insurance":
            for group in conf["priceByPriceGroup"]:
                if group["id"] == cfg["price_group"]:
                    return group["price"]
    return None


def scrape_zermatt(cfg):
    """All days of the season for Zermatt (incl. Cervinia)."""
    session = requests.Session()  # keeps the shop's session cookie (PHPSESSID)
    session.headers.update({"Accept": "application/json, text/plain, */*",
                            "X-Requested-With": "XMLHttpRequest",
                            "Referer": cfg["shop"],
                            "User-Agent": USER_AGENT})
    session.get(cfg["shop"], timeout=20)  # open the shop page once → session cookie

    first = pd.Timestamp(year=MONTHS[0][0], month=MONTHS[0][1], day=1)
    last = pd.Timestamp(year=MONTHS[-1][0], month=MONTHS[-1][1], day=1) + pd.offsets.MonthEnd(0)

    rows = []
    for day in pd.date_range(first, last).strftime("%Y-%m-%d"):
        price = fetch_zermatt_day(session, cfg, day)
        if price is not None:
            rows.append({"date": day, "price": price})
        time.sleep(1)  # politeness: ~150 requests → about 3 minutes
    return pd.DataFrame(rows, columns=["date", "price"])


# ---------- parser 6: Peaksolution (Crans-Montana, Aletsch, Belalp; one POST request per day) ----------

def fetch_peaksolution_day(cfg, day):
    """Adult online price (CHF) for one day; None if no ticket is sold that day."""
    url = cfg["shop"] + "/web/proxy/peaksolution/b2c/b2capi/skipass/offers"
    headers = {"Accept": "application/vnd.alturos.ecommerce.b2capi+json; version=5.0",
               "Content-Type": "application/json",
               "Origin": cfg["shop"],
               "Referer": cfg["shop"] + "/",
               "User-Agent": USER_AGENT}
    body = {"date": day, "region": cfg["region"], "duration": "DR1"}  # DR1 = 1 day
    r = requests.post(url, headers=headers, json=body, timeout=20)
    if r.status_code != 200:
        return None

    for offer in r.json():  # empty list = no ticket that day
        for variant in offer["variants"]:
            if variant["name"] == cfg["variant_name"]:
                return variant["price"]["value"]  # online price (originalPrice = counter price)
    return None


def scrape_peaksolution(cfg):
    """All days of the season for one Peaksolution resort."""
    first = pd.Timestamp(year=MONTHS[0][0], month=MONTHS[0][1], day=1)
    last = pd.Timestamp(year=MONTHS[-1][0], month=MONTHS[-1][1], day=1) + pd.offsets.MonthEnd(0)

    rows = []
    for day in pd.date_range(first, last).strftime("%Y-%m-%d"):
        price = fetch_peaksolution_day(cfg, day)
        if price is not None:
            rows.append({"date": day, "price": price})
        time.sleep(1)  # politeness: ~150 requests → about 3 minutes
    return pd.DataFrame(rows, columns=["date", "price"])


# one function per platform; the resort config says which one to use
PARSERS = {"pricenow": scrape_pricenow, "adelboden": scrape_adelboden,
           "verbier": scrape_verbier, "grimentz": scrape_grimentz,
           "zermatt": scrape_zermatt, "peaksolution": scrape_peaksolution}


def main():
    # display names from the clean resort table (resort_id → resort)
    names = pd.read_csv(ROOT / "data_clean" / "resorts.csv").set_index("resort_id")["resort"]

    # optional: only the resorts named on the command line, e.g.
    #   python scripts/scrape_prices.py crans_montana
    selected = sys.argv[1:] or list(RESORTS)

    frames = []
    for rid in selected:
        cfg = RESORTS[rid]
        df = PARSERS[cfg["parser"]](cfg)
        if "season_start" in cfg:  # optional: drop days before the area opens
            df = df[pd.to_datetime(df["date"]) >= cfg["season_start"]]
        df["resort_id"] = rid
        df["resort"] = names[rid]
        df["source"] = cfg["parser"]
        frames.append(df)
        print(f"{rid}: {len(df)} days")

    new = pd.concat(frames, ignore_index=True)
    new["scraped_on"] = date.today()
    new["days_ahead"] = (pd.to_datetime(new["date"]) - pd.to_datetime(new["scraped_on"])).dt.days
    new = new[["resort_id", "resort", "date", "price", "source", "scraped_on", "days_ahead"]]
    new = new.astype({"date": str, "scraped_on": str})

    # keep earlier scrapes (one row per resort, date and scrape day)
    if OUT.exists():
        new = pd.concat([pd.read_csv(OUT), new], ignore_index=True)
        new = new.drop_duplicates(["resort_id", "date", "scraped_on"], keep="last")

    new.to_csv(OUT, index=False)
    print(f"Saved {len(new)} rows to {OUT}")


if __name__ == "__main__":
    main()