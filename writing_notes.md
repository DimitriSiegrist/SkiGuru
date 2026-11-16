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
