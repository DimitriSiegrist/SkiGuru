"""Clean docs/resort_attributes.csv and write data_clean/resorts.csv.

Run from the repo root:  python scripts/clean_resorts.py
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs" / "resort_attributes.csv"
OUT = ROOT / "data_clean" / "resorts.csv"


def make_id(name):
    """Resort name → merge key, e.g. 'Davos Klosters – Parsenn' → 'davos_klosters_parsenn'."""
    name = name.lower()
    for umlaut, repl in {"ä": "ae", "ö": "oe", "ü": "ue"}.items():
        name = name.replace(umlaut, repl)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()  # é → e
    return re.sub(r"[^a-z0-9]+", "_", name).strip("_")


def main():
    df = pd.read_csv(RAW)
    # types
    df["resort"] = df["resort"].str.strip()
    df["collected_on"] = pd.to_datetime(df["collected_on"])
    for col in ["rating_family", "rating_freeride", "rating_park"]:
        df[col] = df[col].astype("Int64")   # whole stars, missing stays <NA>

    # merge key
    df.insert(0, "resort_id", df["resort"].map(make_id))
    assert df["resort_id"].is_unique, "two resorts have the same resort_id"

    # save
    OUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Saved {len(df)} resorts to {OUT}")


if __name__ == "__main__":
    main()