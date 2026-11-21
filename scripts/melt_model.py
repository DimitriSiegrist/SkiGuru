"""Fits the snow melt model: how much snow depth is lost on a day without new snow."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from src.melt import KEEP, MODEL, forecast, sun_index

SNOW = BASE / "data_clean" / "daily_snow.parquet"
TEMPERATURE = BASE / "data_clean" / "daily_temp.parquet"
TEMPERATURE_RECENT = BASE / "data_clean" / "daily_temp_recent.parquet"

MIN_DEPTH = 20     # cm of snow the day before
MIN_READINGS = 44  # of 48 half-hourly temperature values
MAX_CHANGE = 30    # cm per day, anything beyond is a measuring error
LAST_TRAINING_WINTER = 2019  # later winters are kept aside to test the model
BAND = 0.95        # share of past forecasts the band on the page should cover

CHOSEN = "D  C + fresh snow"
MODELS = {
    "A  depth + degrees": ["HS_before", "warmth"],
    "B  A + fresh snow": ["HS_before", "fresh", "warmth"],
    "C  depth + degrees x sun": ["HS_before", "warm_sun"],
    "D  C + fresh snow": ["HS_before", "fresh", "warm_sun"],
}


def load_temperature():
    """Archive plus the days added since by scripts/update_temperature.py."""
    temp = pd.read_parquet(TEMPERATURE)
    if TEMPERATURE_RECENT.exists():
        temp = pd.concat([temp, pd.read_parquet(TEMPERATURE_RECENT)], ignore_index=True)
    temp["station_code"] = temp["station_code"].astype(str)
    return temp.drop_duplicates(["station_code", "date"], keep="last")


def full_calendar(snow):
    """One row per station and calendar day, so that one row back is exactly one day back."""
    parts = []
    for code, group in snow.groupby("station_code"):
        dates = pd.date_range(group["date"].min(), group["date"].max(), freq="D")
        parts.append(pd.DataFrame({"station_code": code, "date": dates}))
    return pd.concat(parts, ignore_index=True)


def all_days():
    """Every station and calendar day with everything the model needs."""
    snow = pd.read_parquet(SNOW)
    snow["station_code"] = snow["station_code"].astype(str)
    temp = load_temperature()

    days = full_calendar(snow)
    days = days.merge(snow[["station_code", "date", "HS", "HN_1D"]], on=["station_code", "date"], how="left")
    days = days.merge(temp[["station_code", "date", "TA_mean", "n"]], on=["station_code", "date"], how="left")
    days = days.sort_values(["station_code", "date"]).reset_index(drop=True)
    days["hyear"] = days["date"].dt.year + (days["date"].dt.month >= 10).astype(int)

    station = days["station_code"]
    days["HS_before"] = days.groupby(station)["HS"].shift(1)
    days["HN_before"] = days.groupby(station)["HN_1D"].shift(1)
    days["decline"] = days["HS_before"] - days["HS"]

    # Fresh snow stock: today's new snow counts fully, yesterday's 70 %, the day before 49 % ...
    new_snow = days["HN_1D"].fillna(0)
    stock = 0
    for k in range(21):
        stock = stock + KEEP**k * new_snow.groupby(station).shift(k).fillna(0)
    days["stock"] = stock
    days["fresh"] = stock.groupby(station).shift(1)  # the model uses yesterday's stock

    # The stock is only reliable if new snow was reported on each of the last 11 days
    reported = days["HN_1D"].notna().astype(int)
    days["snow_known"] = reported.groupby(station).rolling(11).sum().reset_index(level=0, drop=True) == 11

    days["warmth"] = days["TA_mean"].clip(lower=0)
    days["sun"] = sun_index(days["date"])
    days["warm_sun"] = days["warmth"] * days["sun"]
    return days


def training_days(days):
    """The days the model is fitted on: snow on the ground and no new snow."""
    keep = (
        days["decline"].notna()
        & days["TA_mean"].notna()
        & (days["n"] >= MIN_READINGS)
        & (days["HS_before"] >= MIN_DEPTH)
        & (days["HN_1D"] == 0)       # no new snow on the day itself
        & (days["HN_before"] == 0)   # and none the day before
        & days["snow_known"]
        & (days["decline"].abs() <= MAX_CHANGE)
    )
    columns = ["station_code", "date", "hyear", "HS_before", "decline", "fresh", "warmth", "sun", "warm_sun"]
    return days.loc[keep, columns].reset_index(drop=True)


def r_squared(actual, predicted):
    """Share of the variation around the mean that the prediction explains."""
    return 1 - ((actual - predicted) ** 2).sum() / ((actual - actual.mean()) ** 2).sum()


def fit(train, columns):
    """Least squares without intercept: no snow and no warmth means no decline.

    Standard errors are clustered by station and by day, because the errors of
    one station on neighbouring days and of all stations on one day belong together.
    """
    groups = np.column_stack([train["station_code"].factorize()[0], train["date"].factorize()[0]])
    model = sm.OLS(train["decline"].astype(float), train[columns].astype(float))
    return model.fit(cov_type="cluster", cov_kwds={"groups": groups})


def compare(days):
    """Fits every model on the winters up to 2019 and tests it on the later ones."""
    train = days[days["hyear"] <= LAST_TRAINING_WINTER]
    test = days[days["hyear"] > LAST_TRAINING_WINTER]
    rows, results = [], {}
    for name, columns in MODELS.items():
        result = fit(train, columns)
        results[name] = result
        rows.append({
            "model": name,
            "parameters": len(columns),
            "R2 train": r_squared(train["decline"], result.predict(train[columns].astype(float))),
            "R2 test": r_squared(test["decline"], result.predict(test[columns].astype(float))),
            "t degrees": result.tvalues[columns[-1]],
        })
    return pd.DataFrame(rows).set_index("model"), results


def dry_spells(days, horizon):
    """Rows that are followed by `horizon` days without new snow. The spells do not overlap."""
    station = days["station_code"]
    usable = (days["HN_1D"] == 0) & days["TA_mean"].notna() & (days["n"] >= MIN_READINGS)
    ahead = sum(usable.groupby(station).shift(-k, fill_value=False) for k in range(1, horizon + 1))
    measured_at_end = days.groupby(station)["HS"].shift(-horizon).notna()
    candidates = days[(ahead == horizon) & (days["HS"] >= MIN_DEPTH) & days["snow_known"] & measured_at_end]

    starts, free_from = [], {}
    for row in candidates.itertuples():
        if row.Index >= free_from.get(row.station_code, 0):
            starts.append(row.Index)
            free_from[row.station_code] = row.Index + horizon
    return starts


def check_forecasts(days, coefficients, horizon):
    """Runs the forecast over real dry spells and compares it with what was measured."""
    rows = []
    for start in dry_spells(days, horizon):
        spell = days.loc[start + 1 : start + horizon]
        predicted = forecast(
            days.at[start, "HS"], days.at[start, "stock"], spell["TA_mean"], spell["date"].iloc[0], coefficients
        )
        rows.append({
            "hyear": days.at[start, "hyear"],
            "start": days.at[start, "HS"],
            "measured": spell["HS"].iloc[-1],
            "predicted": predicted.iloc[-1],
        })
    return pd.DataFrame(rows)


def summarise(spells, first_winter=None):
    """Forecast quality, on all winters or from one winter on. Spells where both end at zero are trivial and left out."""
    test = spells[~((spells["measured"] == 0) & (spells["predicted"] == 0))]
    if first_winter is not None:
        test = test[test["hyear"] >= first_winter]
    error = test["predicted"] - test["measured"]
    return {
        "spells": len(test),
        "mean loss (cm)": (test["start"] - test["measured"]).mean(),
        "mean error (cm)": error.abs().mean(),
        "bias (cm)": error.mean(),
        "within 10 cm": (error.abs() <= 10).mean(),
        "R2 of the loss": r_squared(test["start"] - test["measured"], test["start"] - test["predicted"]),
        "band low (cm)": error.quantile((1 - BAND) / 2),
        "band high (cm)": error.quantile((1 + BAND) / 2),
    }


if __name__ == "__main__":
    days = all_days()
    training = training_days(days)
    columns = MODELS[CHOSEN]
    print(f"{len(training):,} days from {training['station_code'].nunique()} stations, "
          f"{(training['hyear'] <= LAST_TRAINING_WINTER).sum():,} of them up to winter {LAST_TRAINING_WINTER}\n")

    # Step 1, validation: fit on the winters up to 2019 only and test on the later ones
    table, results = compare(training)
    print(table.round(3).to_string())

    tested = results[CHOSEN].params.round(5).to_dict()
    unseen = {
        horizon: summarise(check_forecasts(days, tested, horizon), first_winter=LAST_TRAINING_WINTER + 1)
        for horizon in (7, 14, 21)
    }
    print(f"\nForecasts with the coefficients fitted up to {LAST_TRAINING_WINTER}, dry spells since winter {LAST_TRAINING_WINTER + 1}:")
    print(pd.DataFrame(unseen).add_suffix(" days").round(2).to_string())

    # Step 2, final model: the chosen model fitted on all winters, this is what the page uses
    final = fit(training, columns)
    coefficients = final.params.round(5).to_dict()
    r2 = r_squared(training["decline"], final.predict(training[columns].astype(float)))
    summary = pd.DataFrame({"coefficient": final.params, "std error": final.bse, "t": final.tvalues})
    print(f"\nFinal model on all {len(training):,} days, R2 {r2:.3f}")
    print(summary.round({"coefficient": 4, "std error": 5, "t": 1}).to_string())

    quality = {horizon: summarise(check_forecasts(days, coefficients, horizon)) for horizon in (7, 14, 21)}
    print("\nForecasts with the final coefficients, dry spells of all winters:")
    print(pd.DataFrame(quality).add_suffix(" days").round(2).to_string())

    # The page needs the coefficients, the errors for the band and the figures for its results table
    errors = {
        str(horizon): {"low": round(result["band low (cm)"], 1), "high": round(result["band high (cm)"], 1)}
        for horizon, result in quality.items()
    }
    figures = {
        "std_errors": final.bse.round(5).to_dict(),
        "t_values": final.tvalues.round(1).to_dict(),
        "observations": len(training),
        "stations": int(training["station_code"].nunique()),
        "first_winter": int(training["hyear"].min()),
        "r2": round(r2, 3),
        "validation_winter": LAST_TRAINING_WINTER,
        "r2_test": round(table.loc[CHOSEN, "R2 test"], 3),
        "spells_14": int(quality[14]["spells"]),
        "error_14": round(quality[14]["mean error (cm)"], 1),
    }
    MODEL.write_text(json.dumps({"coefficients": coefficients, "errors": errors, "results": figures}, indent=2) + "\n")
    print(f"\nSaved to {MODEL.relative_to(BASE)}")