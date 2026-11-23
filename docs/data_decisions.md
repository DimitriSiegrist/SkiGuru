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

## Prices for all resorts (task 11.1, 19 Nov 2026)
- Structure: `scripts/scrape_prices.py` has one parser per ticketing platform and one config per resort (`RESORTS`); `data_clean/prices.csv` now has `resort_id` (merge key) and `source` (which parser)
  - Reason: many resorts share a platform (Pricenow, Peaksolution, Deskline) → a new resort on a known platform is one config entry, not new code
- Price = adult 1-day pass, online price without basket discounts (e.g. early-booking or family discounts), season Dec 2026 – Apr 2027, scrape 18–19 Nov 2026
- 21 resorts from live shop data (one request per day or per month, 1–2 s pause between requests):
  - Pricenow: Engelberg, Laax, Chäserrugg; own APIs: Adelboden-Lenk, Verbier/4 Vallées, Grimentz-Zinal, Zermatt, Arosa Lenzerheide
  - Peaksolution: Crans-Montana, Aletsch, Belalp; Deskline: Leukerbad, Savognin, Saas-Fee; Davos webshop: Parsenn, Jakobshorn, Rinerhorn, Madrisa
  - Jungfrau (3 areas): API gives only a price level per day (regular / high) → mapped to the tariff CHF 79 / 83 (checked in the shop)
- 4 resorts from fixed tariffs (`source = tariff`, no usable price API): Andermatt-Sedrun (92, premium days 99), Flumserberg (72 Mon–Fri, 76 weekends and holidays), Stoos (58), Hoch-Ybrig (62)
  - Season dates partly assumed (Flumserberg 12 Dec – 29 Mar, end of Stoos and Hoch-Ybrig 29 Mar), because the shops do not sell tickets yet → check in December
- Closed days: some APIs also price days when the area is closed (Grimentz, Leukerbad) → only the days bookable in the shop are kept (`season_start`, `open_periods` in the config)
- Zermatt: price of the International pass (incl. Cervinia), because the attributes include the Italian pistes
- Shared passes: Parsenn and Jakobshorn are only sold together (same price); the three Jungfrau areas share one regional pass
- Flat prices despite "dynamic pricing": Crans-Montana (79), Belalp (70), Saas-Fee (86), Grimentz (75) currently show the same online price every day → weekly re-scrapes (11.3) show whether they start to vary
- Range across all resorts: CHF 30 (Arosa, early December) to CHF 122 (Zermatt International, Christmas)

## Car for all resorts (task 13, 20 Nov 2026)
- Parking: daily rate of the car park at (or nearest to) the valley station for every resort, as for Engelberg (`docs/car_parking.csv`)
  - Reason: most car parks publish only a daily rate; for a ski day of 8–10 h, hourly or 12-h tariffs would be CHF 0–4 cheaper (e.g. Saas-Fee CHF 16 up to 12 h instead of CHF 20 per day; Belalp CHF 1.50/h, max CHF 16) → small next to K (CHF 35–170), same direction for all resorts, easy to explain
  - Where a car park has no daily rate (only hourly or 8-h tariffs), the price for a ski day of about 9 h is used (arrive ~08:00, leave ~17:00), same rule for all resorts:
    - Davos Parsenn and Jakobshorn: CHF 5 for the first 5 h, then CHF 1/h → CHF 9
    - Crans-Montana (Crans-Cry d'Er): CHF 4/h in winter, capped at CHF 32/day → CHF 32
    - Andermatt (P1/P2 at the station): "over 2 hours" CHF 9
    - Jungfrau: 8-h tariffs (Grindelwald Eiger+ CHF 20 for First, Stechelberg CHF 8 for Mürren) and the 2–24 h tariff (Grindelwald Terminal CHF 15 for Kleine Scheidegg/Männlichen)
- Shuttle to car-free resorts (Zermatt: train Täsch–Zermatt CHF 17.20 return, adult): stored as the full adult fare in `extra_chf_return` (`docs/car_parking.csv` → `data_clean/travel_car.csv`); the user's travel pass is applied in `src/finder.py` (task 15.2): GA → 0, Halbtax → 50 % (MGB: shuttle free with GA, half price with Half Fare)
  - Reason: same logic as train mode (the travel pass lowers the user's fare); the CSV stays independent of the user
- Winter-closed passes (task 13, 21 Nov 2026): ORS ignores seasonal closures and routed Aletsch and Belalp via the Gotthard tunnel and the Nufenen pass (closed in winter; Google Maps showed the closure) → ORS now avoids small boxes around the summits of Nufenen, Grimsel, Furka and Susten (`CLOSED_PASSES`, `avoid_polygons` in `scripts/travel_car.py`)
  - Check against Google Maps (20 Nov, Friday evening traffic): ORS times within about ±25 min for all Valais resorts; Verbier, Crans-Montana, Grimentz via Lausanne (no car train)
- Car trains: Leukerbad, Zermatt (Täsch), Saas-Fee, Belalp via Lötschberg (Kandersteg–Goppenstein), Aletsch Arena via Furka (Realp–Oberwald); route checked with ORS (`waycategory` ferry ≈ 17 km)
  - Fares per car incl. passengers, single: Lötschberg CHF 28 Mon–Thu, CHF 31 Fri–Sun and public holidays (BLS, counter price; online CHF 2 cheaper, exact online prices not published); Furka CHF 33 every day (ADAC; MGB price page lists no car prices)
  - Stored as return fares (same day out and back) in two columns, `car_train_chf_mon_thu` (Lötschberg 56, Furka 66) and `car_train_chf_fri_sun` (Lötschberg 62, Furka 66) in `docs/car_parking.csv` → `data_clean/travel_car.csv`; `k_car` stays without the car train; `src/finder.py` adds the fare matching the chosen date (task 15.2): Fri–Sun and public holidays on Mon–Thu (in the season only Easter Monday, 29 Mar 2027) → weekend fare
  - Reason: the app knows the ski day, so the real price for that day is used instead of one assumed price per resort
  - Car train fare kept separate from `extra_chf_return`: GA and Halbtax are not valid on car trains (BLS), but they are on the Zermatt shuttle → the travel-pass discount in `finder.py` must only apply to `extra_chf_return`

## Snow for all resorts (task 14, 23 Nov 2026)
- Matching rule (replaces "nearest station" from 8.5): nearest IMIS snow station (`type == "snow"`) to the valley station that is ≤ 15 km away, has measured since 2016 or earlier (≥ 10 winters for the median) and lies at ski-area altitude (≥ 1800 m, or top altitude − 300 m for low resorts); if no station fulfils all rules, the altitude rule is dropped, then the nearest station is taken → column `match_rule` in `data_clean/resort_stations.csv`
- Result: 22 resorts fulfil all rules; Toggenburg and Flumserberg without the altitude rule (AMD2 Bärenfall, 1610 m, 12.6 / 13.3 km); Arosa Lenzerheide = nearest (ROT3 Plang Bi, data only since 2018 → median from 8 winters)
- Changes vs. nearest station: Davos Parsenn SLF2 → WFJ2 Weissfluhjoch and Jakobshorn SLF2 → DAV3 Hanengretji (SLF2 at 1563 m is in the valley); Andermatt GOS3 → URS2 Giltnasen (GOS3 only since 2021); Flumserberg ENG2 → AMD2 Bärenfall (ENG2 only since 2019)
- Shared stations → identical snow values: Aletsch Arena / Belalp (BEL2), Jakobshorn / Rinerhorn (DAV3), Toggenburg / Flumserberg (AMD2) → snow cannot separate these pairs
- Checks (23 Nov): 25 resorts × 151 days, no missing values; all stations with data up to 22 Nov except OTT2 Ottere (Adelboden, last value 30 Oct) → check again mid-December; alternative FAE2 Färmel (1971 m, 6.2 km, since 1997)
- Expected snow depth on 15 Jan: 62–189 cm; most at the northern Alpine rim and in western Valais (Stoos, Crans-Montana, Leukerbad), less in inner Valais (Saas-Fee 82 cm) → precipitation matters more than altitude
- Cap 150 cm: Stoos, Crans-Montana and Leukerbad all at x_snow_depth = 1 on 15 Jan → snow depth does not separate the snowiest resorts; revisit in task 16
- Merge key `resort_id` added to both snow tables (`resort` kept as readable name); `src/finder.py` switches to `resort_id` in task 15.1

## Merging the finder tables (task 15.1, 23 Nov 2026)
- `merge_tables()` in `src/finder.py` joins all inputs into one table with one row per resort and date (25 resorts × 151 days, 1 Dec–30 Apr = 3,775 rows); merge key `resort_id` everywhere (`resort_id` added to `data_clean/travel_train.csv`, the last table that only had the name)
- Prices: the weekly scraper appends, so a resort can have 2–4 prices for the same day → the latest scrape (`scraped_on`) is used
  - Reason: dynamic prices change as the date gets closer; the newest price is closest to what the user will pay
- Snow table as the base (all 151 days for every resort); days without a price (outside the resort's season) are kept with `price = NaN` (666 resort-days) instead of being dropped
  - Reason: the app can say "no price for this date" instead of the resort silently disappearing from the ranking (task 17.5)
- `validate=` on every merge → pandas raises an error if a key is unexpectedly duplicated, so a duplicate price or resort cannot silently multiply rows

## Consumer surplus for all resorts (task 15.2, 23 Nov 2026)
- `merge_tables()` also keeps `extra_chf_return` (shuttle fare, already included in `k_car`), so the travel-pass discount on the shuttle can be applied in `finder.py`
- Difficulty mix: x̃_difficulty = share of piste km at the user's level (beginner → `km_blue`, intermediate → `km_red`, expert → `km_black`, divided by `piste_km`), scaled with a fixed range per colour = real min/max of the 25 resorts rounded outward to 0.05: blue 0.05–0.65 (real 0.07–0.62), red 0.20–0.80 (real 0.22–0.80), black 0.00–0.40 (real 0.04–0.36) → `LEVEL_RANGES` in `src/finder.py`
  - Reason: the raw shares differ a lot by colour (median blue 0.30, red 0.52, black 0.14); used directly as x̃, the best resort would get at most CHF 3.60 of the CHF 10 weight for an expert but CHF 8 for an intermediate → with a range per colour, the weight means "best vs. worst resort for your level" for every level
  - Same rule as the other attributes (task 10.3): fixed, not min-max across the list, so B does not change when a resort is added
  - Limitation: the share ignores the absolute km (a small resort with a high black share scores fully for experts); size is covered by `piste_km`
- Car train (Lötschberg, Furka): `travel_cost()` adds `car_train_chf_fri_sun` on Fri–Sun and on public holidays Mon–Thu, otherwise `car_train_chf_mon_thu`; the only Mon–Thu holiday in the season is Easter Monday (29 Mar 2027, `HOLIDAYS`); 25 Dec 2026 and 1 Jan 2027 are Fridays anyway
- Travel pass in car mode: `PASS_DISCOUNT` (GA 100 %, Halbtax 50 %) is subtracted from `extra_chf_return` (Zermatt shuttle Täsch–Zermatt), which is already in `k_car`; the car train stays at full price → the travel-pass input on page 3 is now active in car mode too
- Train mode unchanged: stored sbb.ch fares (`fare_full_return`, `fare_halbtax_return`, GA = 0), not `PASS_DISCOUNT`, to keep the sbb.ch rounding
- Default weight for the difficulty mix: CHF 10 (decided in task 9), added to `DEFAULT_WEIGHTS`

## Budget filter and ranking (task 15.3, 23 Nov 2026)
- `rank_resorts()` in `src/finder.py`: budget filter on the money spent, P + K ≤ budget; the time cost v·T is not counted
  - Reason: the budget is what the user can pay out of pocket; v·T is an opportunity cost, not a payment (it still enters the CS)
- Resorts without a price on the chosen date (outside their season) are dropped from the ranking; page 3 can list them separately with `cs[cs["P"].isna()]` (task 17.5)
- Resorts with negative CS stay in the ranking (sorted last); whether they are shown as "not worth the trip" is decided in 17.2

## Test of the CS module (task 15.4, 23 Nov 2026)
- `tests/test_finder.py`: 3 made-up resorts with values at the top, middle and bottom of every fixed reference range, so x̃ = 1, 0.5, 0 and B, K, v·T and CS can be calculated by hand; covers train and car (car train by weekday, Easter Monday, shuttle discount by travel pass), the budget filter and a missing price → all pass
- Made-up data instead of real resorts: real values give x̃ with many decimals, so a hand calculation would only check the code against itself; the toy values make every expected number exact
