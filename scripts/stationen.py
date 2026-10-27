"""Liest die IMIS-Stationen aus den KML-Dateien und schreibt sie als CSV."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

BASIS = Path(__file__).resolve().parent.parent
KML = {"kml": "http://www.opengis.net/kml/2.2"}


def lies_kml(dateiname, typ):
    """Liest eine KML-Datei und gibt eine Tabelle mit einer Zeile pro Station."""
    baum = ET.parse(BASIS / "data_raw" / dateiname)
    zeilen = []

    for ort in baum.iter("{http://www.opengis.net/kml/2.2}Placemark"):
        koord = ort.findtext("kml:Point/kml:coordinates", default="", namespaces=KML)
        if not koord.strip():
            continue

        lon, lat, hoehe = [float(x) for x in koord.strip().split(",")]

        besch = ort.findtext("kml:description", default="", namespaces=KML)
        code = re.search(r"Code:</strong>\s*([A-Za-z0-9]+)", besch)
        beginn = re.search(r"Messbeginn:</strong>\s*(\d{4})", besch)

        zeilen.append({
            "station_code": code.group(1) if code else None,
            "name": ort.findtext("kml:name", default="", namespaces=KML).strip(),
            "typ": typ,
            "lat": lat,
            "lon": lon,
            "hoehe": hoehe,
            "messbeginn": int(beginn.group(1)) if beginn else None,
        })

    return pd.DataFrame(zeilen)


stationen = pd.concat([
    lies_kml("IMIS_SNOW_DE.kml", "schnee"),
    lies_kml("IMIS_WIND_DE.kml", "wind"),
    lies_kml("IMIS_SPECIAL_DE.kml", "spezial"),
], ignore_index=True)

print(len(stationen), "Stationen insgesamt")
print(stationen["typ"].value_counts().to_string())
print()

# --- Abgleich mit den Schneedaten ---
schnee = pd.read_csv(BASIS / "data_raw" / "daily_snow.csv", usecols=["station_code"])

codes_daten = set(schnee["station_code"].unique())
codes_liste = set(stationen["station_code"].dropna())

print("Codes in der Stationsliste:", len(codes_liste))
print("Codes in den Schneedaten  :", len(codes_daten))
print("In beiden                 :", len(codes_liste & codes_daten))
print()
print("Schneedaten ohne Metadaten:", sorted(codes_daten - codes_liste))

# --- Speichern ---
stationen = stationen.dropna(subset=["station_code"]).sort_values("station_code")
stationen.to_csv(BASIS / "data_clean" / "stationen.csv", index=False)
print()
print(len(stationen), "Stationen gespeichert nach data_clean/stationen.csv")