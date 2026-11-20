"""Reads the IMIS stations from the KML files and writes them as CSV."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
KML = {"kml": "http://www.opengis.net/kml/2.2"}


def read_kml(filename, station_type):
    """Reads one KML file and returns a table with one row per station."""
    tree = ET.parse(BASE / "data_raw" / filename)
    rows = []

    for placemark in tree.iter("{http://www.opengis.net/kml/2.2}Placemark"):
        coords = placemark.findtext("kml:Point/kml:coordinates", default="", namespaces=KML)
        if not coords.strip():
            continue

        lon, lat, elevation = [float(x) for x in coords.strip().split(",")]

        # The SLF files are in German, so the label to look for is "Messbeginn"
        description = placemark.findtext("kml:description", default="", namespaces=KML)
        code = re.search(r"Code:</strong>\s*([A-Za-z0-9]+)", description)
        start = re.search(r"Messbeginn:</strong>\s*(\d{4})", description)

        rows.append({
            "station_code": code.group(1) if code else None,
            "name": placemark.findtext("kml:name", default="", namespaces=KML).strip(),
            "type": station_type,
            "lat": lat,
            "lon": lon,
            "elevation": elevation,
            "start_year": int(start.group(1)) if start else None,
        })

    return pd.DataFrame(rows)


stations = pd.concat([
    read_kml("IMIS_SNOW_DE.kml", "snow"),
    read_kml("IMIS_WIND_DE.kml", "wind"),
    read_kml("IMIS_SPECIAL_DE.kml", "special"),
], ignore_index=True)

print(len(stations), "stations in total")
print(stations["type"].value_counts().to_string())
print()

# --- Compare with the snow data ---
snow = pd.read_csv(BASE / "data_raw" / "daily_snow.csv", usecols=["station_code"])

codes_data = set(snow["station_code"].unique())
codes_list = set(stations["station_code"].dropna())

print("Codes in the station list:", len(codes_list))
print("Codes in the snow data   :", len(codes_data))
print("In both                  :", len(codes_list & codes_data))
print()
print("Snow data without metadata:", sorted(codes_data - codes_list))

# --- Save ---
stations = stations.dropna(subset=["station_code"]).sort_values("station_code")
stations.to_csv(BASE / "data_clean" / "stations.csv", index=False)
print()
print(len(stations), "stations saved to data_clean/stations.csv")
