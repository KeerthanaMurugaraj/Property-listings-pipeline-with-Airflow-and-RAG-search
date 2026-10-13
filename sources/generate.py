"""Simulated estate agencies. This stands in for the outside world; it is not part of the pipeline.

The same date always produces the same data. From one day to the next a few
listings appear, a few drop in price and a few disappear.
"""

import csv
import io
import json
import random
from datetime import date
from xml.etree import ElementTree as ET

from listings.config import DATA_DIR

EPOCH = date(2026, 10, 1)
SOURCES_DIR = DATA_DIR / "sources"

COMMUNES = [
    ("Luxembourg-Kirchberg", "1855"), ("Luxembourg-Gare", "1616"), ("Luxembourg-Belair", "1420"),
    ("Esch-sur-Alzette", "4010"), ("Differdange", "4530"), ("Dudelange", "3440"),
    ("Strassen", "8010"), ("Bertrange", "8080"), ("Hesperange", "5880"),
    ("Mersch", "7520"), ("Ettelbruck", "9010"), ("Diekirch", "9210"),
]
STREETS = [
    "Rue de la Gare", "Avenue de la Liberté", "Rue du Fort", "Boulevard Royal",
    "Rue des Roses", "Route d'Arlon", "Rue de l'Eglise", "Rue du Moulin",
]
FEATURES = ["balcony", "parking", "garden", "lift", "furnished", "cellar"]
FRENCH = {
    "apartment": "Appartement", "house": "Maison", "studio": "Studio",
    "balcony": "balcon", "parking": "parking", "garden": "jardin",
    "lift": "ascenseur", "furnished": "meublé", "cellar": "cave",
}
GERMAN = {
    "apartment": "Wohnung", "house": "Haus", "studio": "Studio",
    "balcony": "Balkon", "parking": "Parkplatz", "garden": "Garten",
    "lift": "Aufzug", "furnished": "möbliert", "cellar": "Keller",
}


def _properties() -> list[dict]:
    rng = random.Random(42)
    properties = []
    for i in range(60):
        kind = rng.choices(["apartment", "house", "studio"], weights=[6, 2, 2])[0]
        bedrooms = {"studio": 0, "apartment": rng.randint(1, 3), "house": rng.randint(3, 5)}[kind]
        area = {"studio": 30, "apartment": 35 + bedrooms * 22, "house": 90 + bedrooms * 25}[kind] + rng.randint(-8, 12)
        commune, postcode = rng.choice(COMMUNES)
        first_day = 0 if i < 40 else rng.randint(1, 45)
        properties.append(
            {
                "n": i,
                "kind": kind,
                "bedrooms": bedrooms,
                "area": area,
                "commune": commune,
                "postcode": postcode,
                "street": f"{i + 1} {rng.choice(STREETS)}",
                "price": round(area * rng.uniform(24, 34) / 10) * 10,
                "features": sorted(rng.sample(FEATURES, rng.randint(1, 4))),
                "first_day": first_day,
                "last_day": first_day + rng.randint(5, 40) if rng.random() < 0.3 else None,
                "price_drop_day": first_day + rng.randint(3, 30) if rng.random() < 0.3 else None,
                "agencies": sorted(rng.sample("abc", 2 if rng.random() < 0.3 else 1)),
                "price_missing": rng.random() < 0.08,
            }
        )
    return properties


def _active(agency: str, day: date) -> list[dict]:
    """The properties this agency lists on this day, with the price valid that day."""
    d = (day - EPOCH).days
    active = []
    for p in _properties():
        if agency not in p["agencies"] or d < p["first_day"]:
            continue
        if p["last_day"] is not None and d >= p["last_day"]:
            continue
        if p["price_drop_day"] is not None and d >= p["price_drop_day"]:
            p["price"] = round(p["price"] * 0.95 / 10) * 10
        active.append(p)
    return active


def render_a(day: date) -> str:
    """Agency A: CSV, prices as text, some fields empty."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["ref", "title", "type", "city", "address", "price", "surface", "bedrooms", "features", "description"])
    for p in _active("a", day):
        title = f"Studio in {p['commune']}" if p["kind"] == "studio" else f"{p['bedrooms']}-bedroom {p['kind']} in {p['commune']}"
        writer.writerow(
            [
                f"A-{1000 + p['n']}",
                title,
                p["kind"],
                p["commune"],
                p["street"],
                "sur demande" if p["price_missing"] else f"{p['price']:,} €".replace(",", "."),
                f"{p['area']} m2",
                p["bedrooms"] or "",
                "; ".join(p["features"]),
                f"Bright {p['kind']} of {p['area']} m² in {p['commune']} with {', '.join(p['features'])}.",
            ]
        )
    return out.getvalue()


def render_b(day: date) -> str:
    """Agency B: JSON, different field names, nested objects."""
    listings = [
        {
            "id": f"b{7000 + p['n']}",
            "headline": f"{p['kind'].title()} for rent, {p['area']} sqm, {p['commune']}",
            "propertyType": p["kind"].upper(),
            "location": {"commune": p["commune"], "postcode": p["postcode"], "street": p["street"].upper()},
            "rent": {"amount": p["price"], "currency": "EUR"},
            "livingArea": p["area"],
            "rooms": {"bedrooms": p["bedrooms"]},
            "amenities": p["features"],
            "text": f"{p['kind'].title()} with {p['bedrooms']} bedroom(s) close to shops and public transport. Includes {', '.join(p['features'])}.",
        }
        for p in _active("b", day)
    ]
    return json.dumps({"date": day.isoformat(), "listings": listings}, indent=2, ensure_ascii=False)


def render_c(day: date) -> str:
    """Agency C: XML, French and German text, area sometimes in square feet."""
    root = ET.Element("annonces", date=day.isoformat())
    for p in _active("c", day):
        words = GERMAN if p["n"] % 2 else FRENCH
        number, street = p["street"].split(" ", 1)
        node = ET.SubElement(root, "annonce", id=f"C{500 + p['n']}")
        ET.SubElement(node, "titre").text = f"{words[p['kind']]} {p['area']} m² - {p['commune']}"
        ET.SubElement(node, "type").text = FRENCH[p["kind"]]
        ET.SubElement(node, "ville").text = p["commune"]
        ET.SubElement(node, "adresse").text = f"{number}, {street.lower()}"
        ET.SubElement(node, "loyer", devise="EUR").text = str(p["price"])
        if p["n"] % 3 == 0:
            ET.SubElement(node, "surface", unite="sqft").text = str(round(p["area"] * 10.764))
        else:
            ET.SubElement(node, "surface", unite="m2").text = str(p["area"])
        ET.SubElement(node, "chambres").text = str(p["bedrooms"])
        features = ET.SubElement(node, "equipements")
        for feature in p["features"]:
            ET.SubElement(features, "equipement").text = FRENCH[feature]
        listed = ", ".join(words[f] for f in p["features"])
        if words is GERMAN:
            text = f"Schöne {words[p['kind']]} mit {p['bedrooms']} Schlafzimmer(n) in {p['commune']}. Ausstattung: {listed}."
        else:
            text = f"{words[p['kind']]} lumineux avec {p['bedrooms']} chambre(s) à {p['commune']}. Équipements : {listed}."
        ET.SubElement(node, "description", lang="de" if words is GERMAN else "fr").text = text
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def write_files(day: date) -> None:
    """Agencies A and C deliver files. Agency B is served by sources/api.py instead."""
    for agency, render, ext in [("agency_a", render_a, "csv"), ("agency_c", render_c, "xml")]:
        path = SOURCES_DIR / agency / f"{day.isoformat()}.{ext}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(day), encoding="utf-8")
