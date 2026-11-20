"""Scrape day-pass prices for Engelberg-Titlis (Pricenow API) and save them to data_clean/prices.csv.

Run from the repo root:  python scripts/scrape_prices.py
"""
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_clean" / "prices.csv"

LOG = ROOT / "logs" / "scrape_prices_log.csv"  # one row per resort and run (task 11.2)

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
    "leukerbad": {
        "parser": "deskline",
        "shop": "https://leukerbad.ch",
        "client": "leukerbad",
        "shop_code": "SAA",
        "service_id": "e2fb9a0d-a17c-42fa-a2b8-47bee03f6ad6",  # ski ticket 1 day
        "product_id": "afd8f7d9-4c23-4c91-8d5a-d2bfb61e73a6",  # adult (CHF 68 on 13 Jan; the other product is 41)
        "lim_add_srv_type": ("31efd700-a114-4f30-80d6-f054fa1b7442,1e97cf6c-81e4-41c2-9d90-7d8eb5f4170d,"
                             "a0bc0a6c-0d0f-4716-9940-eacd1c97ef4c,291afea7-e73b-4b29-9c70-778b3d2414c2"),
        # API also prices closed days → keep only the days bookable in the shop
        "open_periods": [("2026-12-05", "2026-12-06"), ("2026-12-12", "2027-04-04")],
    },
    "savognin": {
        "parser": "deskline_search",
        "shop": "https://www.valsurses.ch",
        "client": "savognin",
        "shop_code": "CH1",
        "provider_id": "ef17832f-6ccf-40ed-9051-a35c2acdbe60",
        "service_id": "02c65dae-c2bf-430f-8c8e-1a66418135aa",
        "product_id": "8c33589b-29cd-4759-b878-469409fd652e",  # Erwachsen (adult)
        "theme": "cb0af051-161c-47e1-b089-0cb9782b9eff",
        "open_periods": [("2026-12-05", "2026-12-06"), ("2026-12-12", "2027-03-29")],
    },
    "arosa_lenzerheide": {
        "parser": "arosa",
        "url": "https://shop.arosalenzerheide.swiss/ajax/ticket-day-price/127",
        "shop": "https://shop.arosalenzerheide.swiss/en/1-day-ski-ticket_ticket_127",
        "ticket_id": "skid-aldprod_35c48fcf-c593-7cba-4472-b9e6a271c54b",  # 1-day ski ticket
    },
    "saas_fee": {
        "parser": "deskline_search",
        "shop": "https://www.saas-fee.ch",
        "client": "saasfee",
        "shop_code": "SAA",
        "provider_id": "3e332610-e10e-4216-a072-c46d8c2a5108",  # Saastal Bergbahnen AG
        "service_id": "4a9e43af-aba2-4d40-8a21-2011be4e920a",   # Saas-Fee | 1 Day
        "product_id": "70de5028-3939-444f-8d24-78516fd58f27",   # Saas-Fee | 1 Day Adulte
    },
    # Davos: the shop only sells Parsenn and Jakobshorn together (region 11664) → same price for both
    "davos_klosters_parsenn": {"parser": "davos", "url": "https://www.davosklostersmountains.ch/en/mountains/webshop/winter-tickets", "region": 11664},
    "davos_klosters_jakobshorn": {"parser": "davos", "url": "https://www.davosklostersmountains.ch/en/mountains/webshop/winter-tickets", "region": 11664},
    "davos_klosters_rinerhorn": {"parser": "davos", "url": "https://www.davosklostersmountains.ch/en/mountains/webshop/winter-tickets", "region": 1237},
    "davos_klosters_madrisa": {"parser": "davos", "url": "https://www.davosklostersmountains.ch/en/mountains/webshop/winter-tickets", "region": 1233},
    # Jungfrau: one ski pass for the whole region → same price for all three areas
    # price per level from the tariff 26/27 (adult): regular 79, high season / weekends 83 (checked in the shop 19 Nov)
    "jungfrau_kleine_scheidegg_maennlichen": {"parser": "jungfrau", "url": "https://jts.jungfrau.ch/api/v1/activities/19fa6d77-9437-44a5-8c19-4184a16912b6/availabilities",
                                              "price_by_level": {"REGULAR": 79, "HIGH": 83}},
    "jungfrau_first": {"parser": "jungfrau", "url": "https://jts.jungfrau.ch/api/v1/activities/19fa6d77-9437-44a5-8c19-4184a16912b6/availabilities", "price_by_level": {"REGULAR": 79, "HIGH": 83}},
    "jungfrau_schilthorn_muerren": {"parser": "jungfrau", "url": "https://jts.jungfrau.ch/api/v1/activities/19fa6d77-9437-44a5-8c19-4184a16912b6/availabilities",
                                    "price_by_level": {"REGULAR": 79, "HIGH": 83}},
    # ---- fallback: fixed tariffs 26/27 (adult, 1 day), collected 19 Nov 2026 ----
    "andermatt_sedrun": {
        "parser": "tariff",
        "price": 92,  # bought online before the ski day (96 on the day)
        "premium_price": 99,
        "premium_periods": [("2026-12-19", "2027-01-03"), ("2027-02-01", "2027-03-07")],
        "open_periods": [("2026-12-01", "2027-04-18")],  # shop: bookable 20 Nov – 18 Apr
    },
    "flumserberg": {
        "parser": "tariff",
        "price": 72, "weekend_price": 76,  # Mon–Fri / Sat, Sun and cantonal holidays (SG)
        "holidays": ["2026-12-25", "2026-12-26", "2027-01-01", "2027-01-02", "2027-03-26", "2027-03-29"],
        "open_periods": [("2026-12-12", "2027-03-29")],  # ASSUMPTION: no dates published yet
    },
    "stoos": {
        "parser": "tariff",
        "price": 58,  # online shop (60 at the ticket office)
        "weekends_only_until": "2026-12-11",  # Fronalpstock chairlifts: weekends only until 11 Dec
        "open_periods": [("2026-12-01", "2027-03-29")],  # end ASSUMPTION: no date published
    },
    "hoch_ybrig": {
        "parser": "tariff",
        "price": 62,
        "open_periods": [("2026-12-10", "2027-03-29")],  # start: tariff valid from 10 Dec; end ASSUMPTION
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


# ---------- parser 7: Deskline / Feratel (Leukerbad; one request per day) ----------

def fetch_deskline_day(cfg, day):
    """Adult price (CHF) for one day; None if the product has no price that day."""
    d = pd.Timestamp(day)
    url = (f"https://webapi.deskline.net/{cfg['client']}/en/addservices/"
           f"{cfg['shop_code']}/services/{cfg['service_id']}")
    params = {
        # the shop writes the date without leading zeros, e.g. 2027-1-13
        "fields": f'axessData(date:"{d.year}-{d.month}-{d.day}"){{startTime,products{{id,price,availability}}}}',
        "limAddSrvType": cfg["lim_add_srv_type"],
    }
    headers = {"accept": "application/json, text/plain, */*",
               "dw-sessionid": f"I{int(time.time() * 1000)}",  # the shop uses "I" + timestamp
               "dw-source": "desklineweb",
               "origin": cfg["shop"],
               "referer": cfg["shop"] + "/",
               "User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    if r.status_code != 200:
        return None

    for block in r.json().get("axessData") or []:
        for product in block.get("products") or []:
            if product["id"] == cfg["product_id"]:
                return product["price"]
    return None


def scrape_deskline(cfg):
    """All days of the season for one Deskline resort."""
    first = pd.Timestamp(year=MONTHS[0][0], month=MONTHS[0][1], day=1)
    last = pd.Timestamp(year=MONTHS[-1][0], month=MONTHS[-1][1], day=1) + pd.offsets.MonthEnd(0)

    rows = []
    for day in pd.date_range(first, last).strftime("%Y-%m-%d"):
        price = fetch_deskline_day(cfg, day)
        if price is not None:
            rows.append({"date": day, "price": price})
        time.sleep(1)  # politeness: ~150 requests → about 3 minutes
    return pd.DataFrame(rows, columns=["date", "price"])


# the exact field list the Savognin shop asks for (copied from the shop's request)
RESULT_FIELDS = ("id,name,isFreeBookable,isOwnAvailability,priceChoosableByGuest{active,minPrice,maxPrice},"
                 "bookInfo{date,startTime,duration,price,insteadPrice,availability,isBookable,"
                 "isBookableOnRequest,isOfferable,paymentCancellationPolicy{cancellationPolicy{"
                 "cancellationTextType,defaultHeaderTextNumber,hasFreeCancellation,lastFreeDate,lastFreeTime,"
                 "textLines{cancellationCalculationType,cancellationNights,cancellationPercentage,"
                 "defaultTextNumber,hasFreeTime,freeTime,cancellationDate}}}}")


def scrape_deskline_search(cfg):
    """Deskline with a search (Savognin): per month, create a search (POST), then read its results (GET)."""
    headers = {"accept": "application/json, text/plain, */*",
               "dw-sessionid": f"M{int(time.time() * 1000)}",  # the shop uses "M" + timestamp
               "dw-source": "desklineweb",
               "origin": cfg["shop"],
               "referer": cfg["shop"] + "/",
               "User-Agent": USER_AGENT}
    results_url = (f"https://webapi.deskline.net/{cfg['client']}/de/addservices/{cfg['shop_code']}/"
                   f"{cfg['provider_id']}/services/{cfg['service_id']}/searchresults/")

    frames = []
    for y, m in MONTHS:
        start = pd.Timestamp(year=y, month=m, day=1)
        end = start + pd.DateOffset(months=1)  # the shop searches up to the 1st of the next month
        # 1) create the search for this month (POST) → the server returns its id and hash code
        body = {"searchObject": {"searchGeneral": {"dateFrom": start.strftime("%Y-%m-%dT00:00:00.000"),
                                                   "dateTo": end.strftime("%Y-%m-%dT00:00:00.000")},
                                 "searchAddService": {"serviceProviders": [cfg["provider_id"]],
                                                      "services": [cfg["service_id"]]}}}
        r = requests.post("https://webapi.deskline.net/searches", headers=headers, json=body, timeout=20)
        if not r.ok:  # show the server's reason, not only the status code
            raise RuntimeError(f"search {y}-{m}: {r.status_code} {r.text[:500]}")
        search_id, hash_code = r.json()["id"], r.json()["hashCode"]
        time.sleep(1)

        # 2) read the prices of all days of the month
        params = {"filterId": "", "fields": RESULT_FIELDS,
                  "sortingFields": "", "currency": "CHF", "hashS": hash_code}
        if "theme" in cfg:  # Savognin's shop sends a theme filter, Saas-Fee's does not
            params["limAddSrvTHEME"] = cfg["theme"]
        for attempt in range(3):  # the results can be empty while the server is still searching
            r = requests.get(results_url + search_id, headers=headers, params=params, timeout=20)
            if r.status_code == 204 or (r.ok and r.text.strip()):
                break
            time.sleep(2)
        if r.status_code == 204:  # no content = no ticket sold in this month (e.g. April after closing)
            time.sleep(2)
            continue
        if not (r.ok and r.text.strip()):
            raise RuntimeError(f"results {y}-{m}: {r.status_code} {r.text[:500]!r}")
        for product in r.json()["data"]:
            if product["id"] == cfg["product_id"]:
                days = pd.DataFrame([{"date": b["date"][:10], "price": b["price"]}
                                     for b in product["bookInfo"] if b["isBookable"]],
                                    columns=["date", "price"])
                # the search also returns the 1st of the next month → keep only this month
                frames.append(days[pd.to_datetime(days["date"]).dt.month == m])
        time.sleep(2)  # politeness: pause between months
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "price"])


# ---------- parser 9: Arosa Lenzerheide (own shop, monthly calendar) ----------

def fetch_arosa_month(cfg, year, month):
    """Day-pass prices (CHF) for one month from the Arosa Lenzerheide shop calendar."""
    params = {"ticketId": cfg["ticket_id"], "year": year, "month": month}
    headers = {"X-Requested-With": "XMLHttpRequest", "Referer": cfg["shop"], "User-Agent": USER_AGENT}
    r = requests.get(cfg["url"], headers=headers, params=params, timeout=20)
    r.raise_for_status()

    rows = [{"date": d["date"][:10], "price": d["price"]}
            for d in r.json()["dates"]["dates"]
            if not d["isDisabled"] and d["price"] > 0]  # isDisabled "1" = no ticket that day
    df = pd.DataFrame(rows, columns=["date", "price"])
    # the calendar also shows days of the neighbouring months → keep only this month
    return df[pd.to_datetime(df["date"]).dt.month == month]


def scrape_arosa(cfg):
    """All months of the season for Arosa Lenzerheide."""
    frames = []
    for y, m in MONTHS:
        frames.append(fetch_arosa_month(cfg, y, m))
        time.sleep(2)  # politeness: pause between requests
    return pd.concat(frames, ignore_index=True)


# ---------- parser 10: Davos Klosters (own webshop, server-rendered HTML, one request per day) ----------

def fetch_davos_day(session, cfg, day):
    """Adult price (CHF) for one day and area; None if the area sells no ticket that day."""
    params = {"ajax": 1, "step": 4, "days": 1, "tickettype": 1,  # step 4 = "Who", 1 day, full day
              "regions": cfg["region"], "datepicker-day": f"{day}T00:00:00"}
    r = session.get(cfg["url"], params=params, timeout=20)
    if r.status_code != 200:
        return None
    try:  # the shop answers with JSON {"success": ..., "html": "<page part>"}
        html = r.json()["html"]
    except ValueError:  # plain HTML (as in the browser)
        html = r.text
    html = re.sub(r"<[^>]+>", " ", html)  # drop the HTML tags, keep the text
    html = re.sub(r"\s+", " ", html)
    # first price after the adult box ("Adult" in English, "Erwachsene" in German)
    m = re.search(r"(?:Adult|Erwachsen).{0,300}?CHF\s*([\d.]+)", html)
    return float(m.group(1)) if m else None


def scrape_davos(cfg):
    """All days of the season for one Davos Klosters area."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "X-Requested-With": "XMLHttpRequest",
                            "Accept-Language": "en", "Referer": cfg["url"]})
    session.get(cfg["url"], timeout=20)  # open the shop page once → session cookie
    # go through steps 2 and 3 once, like the shop: the server keeps days, ticket type and area in the session
    base = {"ajax": 1, "days": 1, "tickettype": 1}
    session.get(cfg["url"], params={**base, "step": 2}, timeout=20)
    session.get(cfg["url"], params={**base, "step": 3, "regions": cfg["region"]}, timeout=20)

    first = pd.Timestamp(year=MONTHS[0][0], month=MONTHS[0][1], day=1)
    last = pd.Timestamp(year=MONTHS[-1][0], month=MONTHS[-1][1], day=1) + pd.offsets.MonthEnd(0)
    rows = []
    for day in pd.date_range(first, last).strftime("%Y-%m-%d"):
        price = fetch_davos_day(session, cfg, day)
        if price is not None:
            rows.append({"date": day, "price": price})
        elif day == "2027-01-13":  # a normal season day without a price → show what the server sent
            r = session.get(cfg["url"], params={**base, "step": 4, "regions": cfg["region"],
                                                "datepicker-day": f"{day}T00:00:00"}, timeout=20)
            text = re.sub(r"<[^>]+>|\s+", " ", r.text)[:400]  # page text without HTML tags
            print(f"  debug {cfg['region']} {day}: status {r.status_code}, {text!r}")
        time.sleep(1)  # politeness: ~150 requests per area → about 3 minutes
    return pd.DataFrame(rows, columns=["date", "price"])


# ---------- parser 11: Jungfrau (jts.jungfrau.ch, price level per day → tariff) ----------

def scrape_jungfrau(cfg):
    """One request for the whole season: the API gives a price level (REGULAR / HIGH) per period,
    the config maps each level to the adult tariff in CHF."""
    first = pd.Timestamp(year=MONTHS[0][0], month=MONTHS[0][1], day=1)
    last = pd.Timestamp(year=MONTHS[-1][0], month=MONTHS[-1][1], day=1) + pd.offsets.MonthEnd(0)
    params = {"from": first.strftime("%Y-%m-%dT00:00"),
              "to": (last + pd.Timedelta(days=1)).strftime("%Y-%m-%dT00:00")}
    r = requests.get(cfg["url"], params=params, headers={"User-Agent": USER_AGENT}, timeout=20)
    r.raise_for_status()

    rows = []
    for period in r.json()["availability"]:
        if period["availability"] != "AVAILABLE":
            continue
        price = cfg["price_by_level"][period["startingPrice"]["level"]]
        start = pd.Timestamp(period["start"][:10])
        end = pd.Timestamp(period["end"][:10])  # end is exclusive (next day 00:00)
        for day in pd.date_range(start, end - pd.Timedelta(days=1)):
            rows.append({"date": day.strftime("%Y-%m-%d"), "price": price})
    df = pd.DataFrame(rows, columns=["date", "price"]).drop_duplicates("date")
    return df[pd.to_datetime(df["date"]).between(first, last)]


# ---------- fallback: fixed tariff rules (no usable price API) ----------

def scrape_tariff(cfg):
    """No request: build one row per open day from the published tariff.
    base price, optional weekend/holiday price and optional premium periods (higher price)."""
    rows = []
    for lo, hi in cfg["open_periods"]:
        for day in pd.date_range(lo, hi):
            d = day.strftime("%Y-%m-%d")
            if cfg.get("weekends_only_until") and d <= cfg["weekends_only_until"] and day.weekday() < 5:
                continue  # early season: open on weekends only
            price = cfg["price"]
            if "weekend_price" in cfg and (day.weekday() >= 5 or d in cfg.get("holidays", [])):
                price = cfg["weekend_price"]
            if any(a <= d <= b for a, b in cfg.get("premium_periods", [])):
                price = cfg["premium_price"]
            rows.append({"date": d, "price": price})
    return pd.DataFrame(rows, columns=["date", "price"])


# one function per platform; the resort config says which one to use
PARSERS = {"pricenow": scrape_pricenow, "adelboden": scrape_adelboden,
           "verbier": scrape_verbier, "grimentz": scrape_grimentz,
           "zermatt": scrape_zermatt, "peaksolution": scrape_peaksolution,
           "deskline": scrape_deskline, "deskline_search": scrape_deskline_search,
           "arosa": scrape_arosa, "davos": scrape_davos,
           "jungfrau": scrape_jungfrau, "tariff": scrape_tariff}


# plausibility limits for one resort's result (task 11.2)
MIN_DAYS = 30                 # shortest real season so far: Rinerhorn, 97 days
PRICE_RANGE = (20, 200)       # CHF; real range so far: 30–122


def check_prices(df):
    """Raise ValueError if the scraped prices of one resort look wrong."""
    if len(df) < MIN_DAYS:
        raise ValueError(f"only {len(df)} days (minimum {MIN_DAYS})")
    lo, hi = PRICE_RANGE
    bad = df[(df["price"] < lo) | (df["price"] > hi)]
    if len(bad):
        raise ValueError(f"{len(bad)} prices outside CHF {lo}–{hi}, e.g. {bad['price'].iloc[0]}")
    if df["date"].astype(str).duplicated().any():
        raise ValueError("same date more than once")


def write_log(ok, failed):
    """Append one row per resort to the log file and print a summary line."""
    now = pd.Timestamp.now(tz="Europe/Zurich").strftime("%Y-%m-%d %H:%M")
    rows = ([{"run_at": now, "resort_id": rid, "status": "ok", "days": n, "error": ""} for rid, n in ok] +
            [{"run_at": now, "resort_id": rid, "status": "failed", "days": 0, "error": err} for rid, err in failed])
    LOG.parent.mkdir(exist_ok=True)  # create the logs/ folder on the first run
    pd.DataFrame(rows).to_csv(LOG, mode="a", header=not LOG.exists(), index=False)
    print(f"{len(ok)} ok, {len(failed)} failed" +
          (": " + ", ".join(r for r, _ in failed) if failed else ""))


def main():
    # display names from the clean resort table (resort_id → resort)
    names = pd.read_csv(ROOT / "data_clean" / "resorts.csv").set_index("resort_id")["resort"]

    # optional: only the resorts named on the command line, e.g.
    #   python scripts/scrape_prices.py crans_montana
    selected = sys.argv[1:] or list(RESORTS)

    frames, failed, ok  = [], [], []
    for rid in selected:
        cfg = RESORTS[rid]
        try:
            df = PARSERS[cfg["parser"]](cfg)
        except Exception as e:  # any error in one shop → skip this resort, keep the others
            failed.append((rid, f"{type(e).__name__}: {e}"))
            print(f"{rid}: FAILED ({type(e).__name__}: {e})")
            continue
        if "season_start" in cfg:  # optional: drop days before the area opens
            df = df[pd.to_datetime(df["date"]) >= cfg["season_start"]]
        if "open_periods" in cfg:  # optional: keep only days inside the open periods
            d = pd.to_datetime(df["date"])
            is_open = pd.Series(False, index=df.index)
            for lo, hi in cfg["open_periods"]:
                is_open |= d.between(lo, hi)
            df = df[is_open]

        try:
            check_prices(df)
        except ValueError as e:  # implausible result → treat like an error, keep the others
            failed.append((rid, str(e)))
            print(f"{rid}: FAILED ({e})")
            continue

        df["resort_id"] = rid
        df["resort"] = names[rid]
        df["source"] = cfg["parser"]

        frames.append(df)
        ok.append((rid, len(df)))
        print(f"{rid}: {len(df)} days")

    if not frames:  # nothing scraped at all → do not touch prices.csv
        print("No resort scraped successfully, prices.csv unchanged")
        write_log(ok, failed)
        return

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

    write_log(ok, failed)


if __name__ == "__main__":
    main()