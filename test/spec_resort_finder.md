# Specifications Resort Finder

## Goal
The resort finder calculates the consumer surplus of selected ski resorts in Switzerland for people who prefer skiing on slopes, ranking the ski resorts which have the highest utility for the user.

## Research Question
- Which ski resort gives a given user the highest net benefit on a given date, once pass price, travel cost and travel time are included?
- How does the ranking change when travel cost and value of time are included, compared with ranking by price alone?

## Model
formula: CS_{r,d} = B_{r,d}(w) - P_{r,d} - K_{r} - v * T_r
- B: money value (CHF) of a ski day at resort r on date d for a user with preference weights w
- B_{r,d} = Σ_k w_k * x̃_{r,k,d}
  - x_{r,k,d}: value of attribute k at resort r on date d
    - examples: piste km, number of lifts, altitude, difficulty mix, snow conditions
    - only snow depends on d
  - w_k: the CHF the user assigns to attribute k (see scaling below)
  - sum over all attributes k = 1, …, J
  - default weights are set so that B for an average resort is roughly an average day-pass price
  - scale each attribute to 0-1: x̃_{r,k} = (x_{r,k} − min_k) / (max_k − min_k)
    - x_{r,k}: raw value of attribute k at resort r (e.g. piste km)
    - min_k, max_k: the lowest and highest value of attribute k across all resorts in the list
    - x̃_{r,k}: the scaled value. The worst resort gets 0, the best gets 1, everyone else lies in between in proportion
    - snow depends on d, so for snow min and max are taken across all resorts and dates
    - the weight w_k is then “CHF I’d pay for the best resort on this attribute compared with the worst”
- P: day-pass price of resort
- K: monetary travel cost
- T: round-trip travel time
- v: user's value of time in CHF per hour
- CS: consumer surplus

## Inputs and Outputs
### Inputs
- start station (or location)
- date
- budget
- value of time (CHF per hour)
- travel option
  - train with: no pass, Halbtax, GA or other
  - car
- preferences for:
  - piste km
  - snow conditions
  - number of lifts
  - altitude (base and top)
  - difficulty mix
  - vertical drop
  - snowmaking share
    - share of a resort’s slopes that can be covered with artificial snow (snow cannons)
  - other preferences:
    - family-friendly
    - freeride options
    - parks

### Outputs
- ranked list of resorts by net value
- chart of price against travel time
- resorts above the budget are filtered out
- breakdown per resort: B against P, K and v * T
- snow outlook from Dimi's module

## Data sources
- day-pass prices for future dates
  - source: resort websites and ticket shops (scraped)
- resort attributes:
  - source: resort websites and public resort lists
- public transport:
  - source: Open Swiss public transport API
- car:
  - source: OpenRouteService plus per-km assumption
- snow:
  - source: MeteoSwiss/IMIS stations
- resort locations:
  - source: resort websites (coordinates, base and top altitude)
  - linking snow data: match each resort to the nearest active snow station (by distance and altitude)

## Assumptions and limitations
- start with a few resorts at first
- the start station is fixed to Zurich for now (other start points optional later)
- benefit (B):
  - additivity: the attributes contribute independently, with no interaction (e.g. more piste km is worth the same on a bad-snow day)
  - linearity: the value is proportional to the scaled attribute, with no diminishing returns
  - the user’s CHF weights reflect their true valuation. They’re stated, not revealed, so they may be inaccurate
  - min-max scaling is fixed by the resort list, so B is relative to the chosen resorts
  - snow conditions at the nearest station represent conditions at the resort (a different altitude or exposure is ignored)
    - snow on a future date is predicted with Dimi's regression (fallback: latest observed snow depth)
      - snow quality for future dates is an estimate and less reliable the further ahead the date is
  - static attributes (piste km, lifts) are constant during the season, and the resort is fully open
- price (P):
  - the scraped price is the price the user actually pays: the adult standard day pass, with no discounts, combo passes or season pass
  - prices were scraped close enough to the chosen date, as dynamic prices may change later
- travel (K, T):
  - door-to-door time: the last stretch (bus, cable car) is included
  - round trip with a fixed travel time per resort: no delays, traffic or timetable variation by date
  - car cost is a fixed CHF per km plus a flat parking fee. Train cost uses full fare, Halbtax or GA as stated
  - the user travels alone. Group travel splits car costs, but each train fare counts separately
  - value of time v is constant and applies equally to all travel time