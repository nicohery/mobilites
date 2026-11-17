#!/usr/bin/env python3
"""Build the Plougoumelen soft-mobility layers: KML for cartes.gouv.fr import, GeoJSON for GIS tools."""

import datetime
import json
import math
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from xml.sax.saxutils import escape

PROJECT_DIRECTORY = Path(__file__).resolve().parent
PLANNED_SOURCE_FILE = PROJECT_DIRECTORY / "data" / "a-venir.geojson"
EXISTING_SNAPSHOT_FILE = PROJECT_DIRECTORY / "data" / "existant-osm.json"
OUTPUT_DIRECTORY = PROJECT_DIRECTORY / "dist"

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OVERPASS_QUERY = """
[out:json][timeout:90];
area["boundary"="administrative"]["admin_level"="8"]["ref:INSEE"="56167"]->.commune;
(
  way["highway"="cycleway"](area.commune);
  way["cycleway"~"^(lane|track)$"](area.commune);
  way["cycleway:both"~"^(lane|track)$"](area.commune);
  way["cycleway:left"~"^(lane|track)$"](area.commune);
  way["cycleway:right"~"^(lane|track)$"](area.commune);
  way["highway"~"^(path|footway|pedestrian|steps|bridleway|track)$"](area.commune);
);
out tags geom;
"""

CATEGORIES = {
    "piste_bande_cyclable": {"label": "Piste ou bande cyclable", "color": "#1a9641", "width": 5, "status": "existant"},
    "voie_partagee": {"label": "Voie verte / chemin partagé piétons-vélos", "color": "#00a99d", "width": 5, "status": "existant"},
    "cheminement_pieton": {"label": "Sentier ou cheminement piéton", "color": "#2c7bb6", "width": 3, "status": "existant"},
    "chemin_rural": {"label": "Chemin rural ou d'exploitation", "color": "#a6761d", "width": 2, "status": "existant"},
    "programme": {"label": "Aménagement programmé (voté ou financé)", "color": "#f28e2b", "width": 7, "status": "à venir"},
    "intention": {"label": "Liaison à créer (discontinuité, demande ou engagement)", "color": "#d6006f", "width": 7, "status": "à venir"},
}

SURFACE_LABELS = {
    "asphalt": "enrobé",
    "concrete": "béton",
    "paving_stones": "pavés",
    "compacted": "stabilisé",
    "fine_gravel": "gravillon fin",
    "gravel": "gravier",
    "unpaved": "non revêtu",
    "dirt": "terre",
    "ground": "terre",
    "grass": "herbe",
    "sand": "sable",
    "wood": "platelage bois",
}

BICYCLE_ACCESS_LABELS = {
    "designated": "aménagé pour les vélos",
    "yes": "vélos autorisés",
    "dismount": "vélo à la main",
    "no": "vélos interdits",
}

OSM_ATTRIBUTION = "© contributeurs OpenStreetMap, licence ODbL"


def fetch(url, form_data=None):
    command = ["curl", "-sS", "--fail", "--max-time", "180", "-A", "plougoumelen-mobilites-build/1.0"]
    if form_data is not None:
        command += ["--data", urllib.parse.urlencode(form_data)]
    return subprocess.run(command + [url], check=True, capture_output=True).stdout


def fetch_overpass():
    for attempt, url in enumerate(OVERPASS_URLS * 2):
        try:
            return json.loads(fetch(url, {"data": OVERPASS_QUERY}))
        except subprocess.CalledProcessError as error:
            print("Overpass %s failed (curl exit %d), trying next server" % (url, error.returncode), file=sys.stderr)
            time.sleep(5 * (attempt + 1))
        except json.JSONDecodeError:
            print("Overpass %s returned an invalid response, trying next server" % url, file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    sys.exit("All Overpass servers failed. Rerun later, or use --offline to rebuild from the last snapshot.")


def classify(tags):
    highway = tags.get("highway", "")
    cycleway_values = {tags.get(key, "") for key in ("cycleway", "cycleway:both", "cycleway:left", "cycleway:right")}
    if highway == "cycleway" or cycleway_values & {"lane", "track"}:
        return "piste_bande_cyclable"
    if highway in ("path", "footway", "pedestrian", "bridleway", "track") and tags.get("bicycle") == "designated":
        return "voie_partagee"
    if highway in ("path", "footway", "pedestrian", "steps", "bridleway"):
        return "cheminement_pieton"
    if highway == "track":
        return "chemin_rural"
    return None


def length_in_meters(coordinates):
    earth_radius = 6371008.8
    total = 0.0
    for (start_longitude, start_latitude), (end_longitude, end_latitude) in zip(coordinates, coordinates[1:]):
        delta_latitude = math.radians(end_latitude - start_latitude)
        delta_longitude = math.radians(end_longitude - start_longitude)
        haversine = (
            math.sin(delta_latitude / 2) ** 2
            + math.cos(math.radians(start_latitude)) * math.cos(math.radians(end_latitude)) * math.sin(delta_longitude / 2) ** 2
        )
        total += 2 * earth_radius * math.asin(math.sqrt(haversine))
    return total


def existing_features(overpass_result):
    features = []
    for element in overpass_result["elements"]:
        if element["type"] != "way" or "geometry" not in element:
            continue
        tags = element.get("tags", {})
        category = classify(tags)
        if category is None:
            continue
        coordinates = [[round(node["lon"], 6), round(node["lat"], 6)] for node in element["geometry"]]
        properties = {
            "identifiant": "osm-way-%d" % element["id"],
            "nom": tags.get("name") or tags.get("ref") or CATEGORIES[category]["label"],
            "categorie": category,
            "statut": "existant",
            "revetement": SURFACE_LABELS.get(tags.get("surface", ""), tags.get("surface", "non renseigné")),
            "velo": BICYCLE_ACCESS_LABELS.get(tags.get("bicycle", ""), "non renseigné"),
            "source": OSM_ATTRIBUTION,
            "source_url": "https://www.openstreetmap.org/way/%d" % element["id"],
        }
        features.append({"type": "Feature", "properties": properties, "geometry": {"type": "LineString", "coordinates": coordinates}})
    return features


def planned_features():
    collection = json.loads(PLANNED_SOURCE_FILE.read_text(encoding="utf-8"))
    for feature in collection["features"]:
        category = feature["properties"].get("categorie")
        if category not in ("programme", "intention"):
            sys.exit("%s: unknown categorie %r in %s" % (feature["properties"].get("identifiant"), category, PLANNED_SOURCE_FILE.name))
    return collection["features"]


def kml_color(hex_color, opacity):
    red, green, blue = hex_color[1:3], hex_color[3:5], hex_color[5:7]
    return "%02x%s%s%s" % (round(opacity * 255), blue, green, red)


def description_html(properties):
    labels = [
        ("categorie", "Type"),
        ("statut", "Statut"),
        ("avancement", "Avancement"),
        ("type_amenagement", "Aménagement prévu"),
        ("echeance", "Échéance"),
        ("revetement", "Revêtement"),
        ("velo", "Vélo"),
        ("longueur_m", "Longueur"),
        ("trace", "Tracé"),
        ("source", "Source"),
    ]
    rows = []
    for key, label in labels:
        value = properties.get(key)
        if value in (None, "", "non renseigné"):
            continue
        if key == "categorie":
            value = CATEGORIES[value]["label"]
        if key == "longueur_m":
            value = "%d m" % value
        rows.append("<b>%s</b> : %s" % (escape(label), escape(str(value))))
    if properties.get("source_url"):
        rows.append('<a href="%s" target="_blank">Voir la source</a>' % escape(properties["source_url"]))
    return "<br/>".join(rows)


def build_kml(document_name, document_description, features):
    used_categories = [category for category in CATEGORIES if any(feature["properties"]["categorie"] == category for feature in features)]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "<Document>",
        "<name>%s</name>" % escape(document_name),
        "<description><![CDATA[%s]]></description>" % document_description,
    ]
    for category in used_categories:
        style = CATEGORIES[category]
        lines += [
            '<Style id="%s">' % category,
            "<LineStyle><color>%s</color><width>%d</width></LineStyle>" % (kml_color(style["color"], 0.9), style["width"]),
            "</Style>",
        ]
    for category in used_categories:
        lines += ["<Folder>", "<name>%s</name>" % escape(CATEGORIES[category]["label"])]
        for feature in features:
            properties = feature["properties"]
            if properties["categorie"] != category:
                continue
            coordinates = " ".join("%s,%s" % (longitude, latitude) for longitude, latitude in feature["geometry"]["coordinates"])
            lines += [
                "<Placemark>",
                "<name>%s</name>" % escape(properties["nom"]),
                "<description><![CDATA[%s]]></description>" % description_html(properties),
                "<styleUrl>#%s</styleUrl>" % category,
                "<LineString><tessellate>1</tessellate><coordinates>%s</coordinates></LineString>" % coordinates,
                "</Placemark>",
            ]
        lines.append("</Folder>")
    lines += ["</Document>", "</kml>", ""]
    return "\n".join(lines)


def with_display_properties(feature):
    properties = dict(feature["properties"])
    style = CATEGORIES[properties["categorie"]]
    properties["libelle"] = style["label"]
    properties["stroke"] = style["color"]
    properties["stroke-width"] = style["width"]
    properties["stroke-opacity"] = 0.9
    return {**feature, "properties": properties}


def main():
    offline = "--offline" in sys.argv
    if offline:
        overpass_result = json.loads(EXISTING_SNAPSHOT_FILE.read_text(encoding="utf-8"))
    else:
        overpass_result = fetch_overpass()
        EXISTING_SNAPSHOT_FILE.write_text(json.dumps(overpass_result, ensure_ascii=False), encoding="utf-8")

    existing = existing_features(overpass_result)
    planned = planned_features()
    for feature in existing + planned:
        feature["properties"]["longueur_m"] = round(length_in_meters(feature["geometry"]["coordinates"]))

    snapshot_date = overpass_result.get("osm3s", {}).get("timestamp_osm_base", "")[:10] or datetime.date.today().isoformat()
    source_note = (
        "Existant : OpenStreetMap au %s (%s).<br/>"
        "À venir : voir data/a-venir.geojson, chaque tracé porte sa source. "
        "Les tracés « Liaison à créer » sont indicatifs." % (snapshot_date, OSM_ATTRIBUTION)
    )

    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    outputs = {
        "plougoumelen-mobilites-douces-existant.kml": build_kml("Plougoumelen – mobilités douces existantes", source_note, existing),
        "plougoumelen-mobilites-douces-a-venir.kml": build_kml("Plougoumelen – mobilités douces à venir", source_note, planned),
        "plougoumelen-mobilites-douces.kml": build_kml("Plougoumelen – mobilités douces", source_note, planned + existing),
        "plougoumelen-mobilites-douces.geojson": json.dumps(
            {"type": "FeatureCollection", "features": [with_display_properties(feature) for feature in planned + existing]},
            ensure_ascii=False,
        ),
    }
    for file_name, content in outputs.items():
        (OUTPUT_DIRECTORY / file_name).write_text(content, encoding="utf-8")

    print("OpenStreetMap snapshot: %s" % snapshot_date)
    for category, style in CATEGORIES.items():
        matching = [feature for feature in existing + planned if feature["properties"]["categorie"] == category]
        total_length = sum(feature["properties"]["longueur_m"] for feature in matching)
        print("  %-55s %3d tronçons  %6.1f km" % (style["label"], len(matching), total_length / 1000))
    print("Written to %s" % OUTPUT_DIRECTORY)


if __name__ == "__main__":
    main()
