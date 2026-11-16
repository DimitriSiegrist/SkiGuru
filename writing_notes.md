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
