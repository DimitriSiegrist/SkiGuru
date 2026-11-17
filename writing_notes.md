# Writing notes (assumptions and data decisions)

## Resort attributes (task 8.1, 11 Nov 2026)
- Source: all resort attributes from Skiresort.info, so every resort is measured the same way (collected 11 Nov 2026)
- Engelberg-Titlis = Titlis area only (Titlis, Trübsee, Jochpass, Gerschnialp): 70 km (18 blue, 42.5 red, 9.5 black)
  - Official 82 km includes Brunni and Fürenalp → excluded (Brunni is a separate resort in `resort_candidates.csv`)
- Lifts: 17 (Skiresort.info resort page); another Skiresort.info list says 18
- Altitude: base 1003 m, top 3020 m, vertical drop 2017 m (Skiresort.info; official base often given as 1050 m)
- Snowmaking: 40 % of the slopes (Skiresort.info)
- Parks = 0: Skiresort.info lists no snow park; other sources mention a park at Jochpass/Engstlenalp → decide one rule for all resorts
- Freeride = 1: Engelberg-Titlis is known for freeride (MySwitzerland)
- Family-friendly = 1: own judgement (5 Kinderländer, beginner slopes at Gerschnialp) → define a rule for all resorts
- Coordinates: Titlis valley station (Gerschnistrasse 12, Engelberg), from Google Maps: 46.8162, 8.3957

## Prices (task 8.2, 16 Nov 2026)
- Source: Pricenow booking API behind shop.titlis.ch (`api.pricenow.dev`, product 180000, endpoint `journey/validities`, one request per month); needs the shop's channel UUID in the header `pratiq-channel-uuid`
- Price = adult day pass (`adult_age20to999`, duration 1d), online price without discounts; API returns prices in Rappen (÷ 100)
- Season covered: 1 Dec 2026 – 30 Apr 2027 (151 days), first scrape 16 Nov 2026: CHF 51–69
- Dynamic pricing: prices change between scrape days (e.g. 1 Dec: CHF 53 on 13 Nov, CHF 54 on 16 Nov) → store `scraped_on` and `days_ahead`; repeated scrapes are appended, not overwritten
- Day passes filtered by ticket label, not by day count: on 28 Mar 2027 (summer-time switch) a 2-day ticket (CHF 120.5) otherwise passed the filter
- Politeness: non-commercial university project (professor confirmed scraping/APIs are fine), 2 s pause between requests, User-Agent names the project

## Train (task 8.3, 16 Nov 2026)
- Travel time: transport.opendata.ch `/v1/connections` (free, no key); fastest of the next 4 connections; reference day Thu 10 Dec 2026, out from 07:00, back from 16:30 (timetable assumed the same on all weekdays)
- Zurich HB → Engelberg: 103 min out, 109 min back, 1 change (Lucerne); + 10 min walk each way station → Titlis valley station → T = 232 min round trip
- Fares: no public SBB price API (OJP Fare on opentransportdata.swiss is beta, XML, needs a key) → looked up once on sbb.ch (16 Nov 2026): return 2nd class, normal fare (no Supersaver): CHF 80 full, CHF 40 Halbtax, GA = CHF 0
- Checked full fare in a private window (logged-in profile pre-fills the Halbtax)
- Zurich city upgrade (CHF 5.90) left out: start point is Zurich HB itself
- K depends on the user's travel pass → stored as both fares in `data_clean/travel_train.csv`, chosen in the app

## Car (task 8.4, 16 Nov 2026)
- Distance and driving time: OpenRouteService Directions V2 (`api.heigit.org/openrouteservice/v2/directions/driving-car`; old URL api.openrouteservice.org shut off 28 Sep 2026), free key stored in `.env` (git-ignored), never in code or chats
- Zurich HB (8.5403, 47.3779) → Titlis valley station: 85.5 km / 76 min out, 86.4 km / 79 min back → 171.9 km, 155 min round trip; no walk (car park at the valley station); no traffic or snow-chain delays
- Cost per km: variable costs only (fuel, tyres, maintenance) = marginal cost of one extra trip for someone who already owns a car: TCS sample car 2026 CHF 4,135 variable costs / 15,000 km ≈ CHF 0.28/km (full cost incl. fixed costs would be CHF 0.74/km)
- Parking: CHF 10/day at Parking Talstation Engelberg-Titlis (parking.ch, winter tariff Nov–Apr); parking.ch lists summer tariff (CHF 5) from 1 Mar, overlapping with winter until 30 Apr → assumed CHF 10 for the whole season
- K_car = 0.2757 × 171.9 + 10 = CHF 57.39 (one person; costs not split among passengers)
- Example with v = CHF 20/h: car K + v·T = 109, train Halbtax 117, train full fare 157

## Snow (task 8.5, 16 Nov 2026)
- Station: nearest active snow station to the valley station → TIT2 Titlisboden (2149 m, 3.5 km, measuring since 1993); next one GAD2 Gschletteregg (8 km)
- Snow data: Dimi's `daily_snow.parquet` (IMIS, measured values only, up to today) → no values for future ski days
- **Fallback until Dimi's snow forecast exists**: historical values per calendar day at the station
  - snow depth = median HS over all winters (33 winters at TIT2)
  - new snow = mean new snow over 3 days, smoothed over ±7 days; new snow only measured since Sep 2011 (complete since then); values > 100 cm/day treated as measurement errors (max 234 cm)
  - IMIS derives new snow automatically → wind drift can push values up
- Scaling with caps: x_snow_depth = min(HS / 150 cm, 1), x_new_snow = min(HN3 / 30 cm, 1) → above ~1.5 m base, more snow adds little for piste skiers (gives up linearity at the top)
- Snow depth and new snow are two separate attributes with their own weights in B

## Consumer surplus (task 8.6, 16 Nov 2026)
- B = B₀ + Σ w_k · x̃_k; B₀ = what a ski day as such is worth to the user (user input, default CHF 150) → CS > 0 means the trip is worth it; B₀ does not change the ranking (same for all resorts)
  - without B₀ (B ≈ day-pass price as in the first spec) CS would be negative for almost every trip, because travel cost and time come on top
- Pilot: fixed reference ranges instead of min-max (min-max needs at least two resorts): piste km 0–300, lifts 0–80, vertical drop 0–2200 m, top altitude 1500–3500 m, snowmaking 0–1, snow depth 0–150 cm, new snow 0–30 cm, family/freeride/parks 0/1
- Default weights (CHF, best vs. worst): piste km 30, lifts 5, vertical drop 15, top altitude 10, snowmaking 5, snow depth 25, new snow 10, family/freeride/parks 5 each; difficulty mix to be added later
- Check: hand calculation = code (15 Jan, train Halbtax, v = 20: B 220.91 − P 58 − K 40 − v·T 77.33 = CS 45.58)
- Season result (train, Halbtax): CS CHF 26–56; lowest around Christmas/New Year (prices CHF 68–69, little snow), weekends visible as dips (CS mirrors the price)
- Limitation: late April has the highest CS (cheapest price, full snow score) → spring snow quality and lift closures not modelled

## Resort list and attributes (tasks 9 and 10.1, 16 Nov 2026)
- Resort list: 20 resorts (column `selected` in `docs/resort_candidates.csv`) = all 13 scrapable + 7 with tariff fallback (Flumserberg, Hoch-Ybrig, Stoos, Jungfrau, Davos Klosters, Arosa Lenzerheide, Andermatt-Sedrun-Disentis); more only if time at the end
- Split into 25 rows in `docs/resort_attributes.csv` (one row per ski area as listed on Skiresort.info):
  - Verbier + Nendaz merged into 'Verbier/4 Vallées' (one area on Skiresort.info); Nendaz replaced by Saas-Fee
  - Zermatt incl. Cervinia (price must be the international pass → check in task 11)
  - Davos Klosters split into Parsenn, Jakobshorn, Rinerhorn, Madrisa (Pischa dropped: 0 km of pistes, freeride only)
  - Jungfrau split into Kleine Scheidegg/Männlichen, First, Schilthorn/Mürren
  - Andermatt = Andermatt/Oberalp/Sedrun (without Gemsstock and Disentis); Toggenburg = Chäserrugg (Pricenow product)
  - Split areas need their own price (Davos and Jungfrau tariffs per area, task 11)
- Attributes and default weights (CHF): piste km 30, lifts 5, vertical drop 15, top altitude 10, snowmaking share 5, difficulty mix 10, snow depth 25, new snow 10, family / freeride / parks 5 each
  - Difficulty mix = share of km at the user's level (beginner / intermediate / expert → blue / red / black km)
- Source: Skiresort.info for all attributes (same measure for every resort); coordinates = valley stations from Google Maps (Crans-Montana and Lenzerheide corrected from mountain/middle station to valley station)
- Family / freeride / parks: Skiresort.info test ratings (1–5 stars), scaled (stars − 1) / 4, instead of 0/1 → finer and one rule for all resorts; Chäserrugg has no test report → neutral 0.5
- Ski routes (e.g. Laax 40 km) not counted in piste km (not groomed; covered by the freeride rating)
- Engelberg lifts 17 → 18 (Skiresort.info, 16 Nov)
- Spot check (Laax, Stoos, Parsenn, Verbier/4 Vallées): all values match Skiresort.info
- Reference ranges for scaling: set once from the real min/max of the resorts (task 10.3), not min-max across the list → B must not depend on which resorts are in the list

## Resort attribute cleaning (task 10.2, 17 Nov 2026)
- Input: `docs/resort_attributes.csv` (hand-collected, versioned in the repo) instead of `data_raw/` → `data_raw/` is not in the repo, so a script reading from it could not be reproduced
- Output: `data_clean/resorts.csv` = the one attribute table that the app and all scripts read; written only by `scripts/clean_resorts.py`
- Types: resort names stripped of leading/trailing spaces (a trailing space would make merges fail silently); `collected_on` as date; star ratings as integers that allow missing values (`Int64`)
- Missing values: only Chäserrugg (Toggenburg) has none of the three ratings (no Skiresort.info test report) → kept as missing (`<NA>`) in `resorts.csv`, not filled with 3 stars
  - Reason: the clean table should only contain what the source says; a filled-in 3 would look like a real Skiresort.info rating
  - The "neutral" assumption sits in one place, the model: `scale()` in `src/finder.py` turns a missing value into 0.5 (= same as 3 stars) → Chäserrugg is neither rewarded nor penalised for family / freeride / parks
- Merge key: new column `resort_id`, generated from the name (lowercase, ä/ö/ü → ae/oe/ue, accents removed, other characters → `_`), e.g. 'Davos Klosters – Parsenn' → `davos_klosters_parsenn`; `resort` stays as the display name
  - Reason: names contain en dashes, `/`, accents and umlauts → easy to mistype in other files (prices, fares, parking), and a mistyped key drops the resort from a merge without an error
  - Script checks that all 25 ids are unique

## Plausibility checks (task 10.3, 17 Nov 2026)
- `check()` in `scripts/clean_resorts.py` runs before saving and stops the script if a value cannot be right → a wrong value never reaches `data_clean/resorts.csv` or the app; checks re-run automatically whenever the data changes
  - vertical drop = top − base altitude (exact)
  - blue + red + black km = piste km (tolerance 0.5 km for decimal rounding)
  - base altitude < top altitude; snowmaking share 0–1; ratings 1–5 stars (missing skipped)
  - coordinates inside a rough box around Switzerland (lat 45.8–47.9, lon 5.9–10.5) → catches swapped lat/lon and typos
- Result: all 25 resorts pass all checks
- Min/max of the 25 resorts: piste km 26–412 (Madrisa – Verbier/4 Vallées), lifts 7–65 (Rinerhorn – Verbier), vertical drop 635–2337 m (Stoos – Zermatt), top altitude 1831–3899 m (Hoch-Ybrig – Zermatt), snowmaking 0.12–0.95, ratings 1–5 stars (freeride 3–5)
- Pilot ranges were too narrow: piste km 0–300 (Verbier and Zermatt both capped at 1 → the two largest areas looked equal), vertical drop 0–2200 (Zermatt capped), top altitude 1500–3500 (Zermatt and Saas-Fee capped); lower bounds of 0 far below every real resort
- New fixed reference ranges = real min/max rounded outward to round numbers: piste km 25–425, lifts 5–70, vertical drop 600–2400 m, top altitude 1800–3900 m; snowmaking 0–1 and ratings 1–5 kept (natural scales)
  - Reason: weights are defined as CHF for the best vs. the worst value → range ≈ worst to best real resort; rounded numbers are easy to explain and leave a little room for resorts added later; set once (not min-max across the list) so B does not change when a resort is added
  - Side effect: lower bounds above 0 → scaled values and B lower for all resorts → CS levels fall (Engelberg lower than in the pilot); differences between resorts become clearer
