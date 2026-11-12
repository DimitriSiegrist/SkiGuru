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
