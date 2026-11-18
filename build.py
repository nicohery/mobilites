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
    "velo": {"short_label": "Vélo", "label": "Vélo : piste ou bande cyclable", "color": "#1a9641", "width": 5},
    "partage": {"short_label": "Partagé", "label": "Partagé piétons-vélos : voie verte", "color": "#00a99d", "width": 5},
    "pieton": {"short_label": "Piéton", "label": "Piéton : sentier, cheminement", "color": "#2c7bb6", "width": 3},
    "chemin_rural": {"short_label": "Chemin rural", "label": "Chemin rural ou d'exploitation", "color": "#a6761d", "width": 2},
}
ENGAGEMENTS = {
    "programme": {"label": "Voté ou financé", "width": 6},
    "intention": {"label": "Étudié ou évoqué (conseil, bulletin)", "width": 4},
    "promesse": {"label": "Promesse de campagne (municipales 2026)", "width": 2},
}

STATUSES = {"existant": "existant", "a-venir": "à venir"}

DOT_LENGTH_METERS = 20
DOT_GAP_METERS = 30

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
        return "velo"
    if highway in ("path", "footway", "pedestrian", "bridleway", "track") and tags.get("bicycle") == "designated":
        return "partage"
    if highway in ("path", "footway", "pedestrian", "steps", "bridleway"):
        return "pieton"
    if highway == "track":
        return "chemin_rural"
    return None


def distance_in_meters(start, end):
    (start_longitude, start_latitude), (end_longitude, end_latitude) = start, end
    delta_latitude = math.radians(end_latitude - start_latitude)
    delta_longitude = math.radians(end_longitude - start_longitude)
    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(math.radians(start_latitude)) * math.cos(math.radians(end_latitude)) * math.sin(delta_longitude / 2) ** 2
    )
    return 2 * 6371008.8 * math.asin(math.sqrt(haversine))


def length_in_meters(coordinates):
    return sum(distance_in_meters(start, end) for start, end in zip(coordinates, coordinates[1:]))


def dotted_segments(coordinates):
    """KML has no dash style, so a dotted line is drawn as many short separate segments."""
    segments = []
    current_segment = []
    position_in_cycle = 0.0
    cycle_length = DOT_LENGTH_METERS + DOT_GAP_METERS
    for start, end in zip(coordinates, coordinates[1:]):
        segment_length = distance_in_meters(start, end)
        travelled = 0.0
        while travelled < segment_length:
            drawing = position_in_cycle < DOT_LENGTH_METERS
            boundary = DOT_LENGTH_METERS if drawing else cycle_length
            step = min(boundary - position_in_cycle, segment_length - travelled)
            ratio_start = travelled / segment_length
            ratio_end = (travelled + step) / segment_length
            point_start = [start[0] + (end[0] - start[0]) * ratio_start, start[1] + (end[1] - start[1]) * ratio_start]
            point_end = [start[0] + (end[0] - start[0]) * ratio_end, start[1] + (end[1] - start[1]) * ratio_end]
            if drawing:
                if not current_segment:
                    current_segment.append(point_start)
                current_segment.append(point_end)
            travelled += step
            position_in_cycle += step
            if position_in_cycle >= cycle_length:
                position_in_cycle = 0.0
            if drawing and position_in_cycle >= DOT_LENGTH_METERS:
                segments.append(current_segment)
                current_segment = []
    if len(current_segment) > 1:
        segments.append(current_segment)
    return segments


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
        properties = feature["properties"]
        if properties.get("categorie") not in CATEGORIES:
            sys.exit("%s: categorie must be one of %s" % (properties.get("identifiant"), ", ".join(CATEGORIES)))
        if properties.get("statut") not in STATUSES.values():
            sys.exit("%s: statut must be one of %s" % (properties.get("identifiant"), ", ".join(STATUSES.values())))
        if properties["statut"] != "existant" and properties.get("engagement") not in ENGAGEMENTS:
            sys.exit("%s: engagement must be one of %s" % (properties.get("identifiant"), ", ".join(ENGAGEMENTS)))
    return collection["features"]


def kml_color(hex_color, opacity):
    red, green, blue = hex_color[1:3], hex_color[3:5], hex_color[5:7]
    return "%02x%s%s%s" % (round(opacity * 255), blue, green, red)


def line_style(properties):
    """Colour tells the type, dots tell a planned link, and a planned link's width tells how firm the commitment is."""
    if properties["statut"] == "existant":
        return LINE_STYLES[properties["categorie"]]
    return LINE_STYLES["%s_%s" % (properties["categorie"], properties["engagement"])]


def line_styles():
    styles = {}
    for category_key, category in CATEGORIES.items():
        styles[category_key] = {"color": category["color"], "width": category["width"], "dotted": False}
        for engagement_key, engagement in ENGAGEMENTS.items():
            styles["%s_%s" % (category_key, engagement_key)] = {"color": category["color"], "width": engagement["width"], "dotted": True}
    return {style_id: {**style, "id": style_id} for style_id, style in styles.items()}


LINE_STYLES = line_styles()


def line_style_declarations():
    """cartes.gouv.fr imports lines with an inline style, or a style id holding digits and hyphens, as invisible."""
    return [
        '<Style id="%s"><LineStyle><color>%s</color><width>%d</width></LineStyle></Style>'
        % (style["id"], kml_color(style["color"], 0.9), style["width"])
        for style in LINE_STYLES.values()
    ]


def draw_order(feature):
    """Later placemarks are drawn on top: planned links above existing ones, cycling above walking."""
    properties = feature["properties"]
    return properties["statut"] != "existant", -list(CATEGORIES).index(properties["categorie"])


def description_html(properties):
    labels = [
        ("categorie", "Type"),
        ("statut", "Statut"),
        ("engagement", "Engagement"),
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
        if key == "engagement":
            value = ENGAGEMENTS[value]["label"]
        if key == "longueur_m":
            value = "%d m" % value
        rows.append("<b>%s</b> : %s" % (escape(label), escape(str(value))))
    if properties.get("source_url"):
        rows.append('<a href="%s" target="_blank">Voir la source</a>' % escape(properties["source_url"]))
    return "<br/>".join(rows)


def coordinates_text(coordinates):
    return " ".join("%.6f,%.6f" % (longitude, latitude) for longitude, latitude in coordinates)


def line_geometry(coordinates, dotted):
    if not dotted:
        return "<LineString><tessellate>1</tessellate><coordinates>%s</coordinates></LineString>" % coordinates_text(coordinates)
    dots = "".join(
        "<LineString><tessellate>1</tessellate><coordinates>%s</coordinates></LineString>" % coordinates_text(segment)
        for segment in dotted_segments(coordinates)
    )
    return "<MultiGeometry>%s</MultiGeometry>" % dots


def line_placemark(name, coordinates, style, description=None):
    lines = ["<Placemark>", "<name>%s</name>" % escape(name)]
    if description:
        lines.append("<description><![CDATA[%s]]></description>" % description)
    lines += [
        "<styleUrl>#%s</styleUrl>" % style["id"],
        line_geometry(coordinates, style["dotted"]),
        "</Placemark>",
    ]
    return lines


def build_kml(document_name, features):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "<Document>",
        "<name>%s</name>" % escape(document_name),
    ] + line_style_declarations()
    for feature in sorted(features, key=draw_order):
        properties = feature["properties"]
        lines += line_placemark(properties["nom"], feature["geometry"]["coordinates"], line_style(properties), description_html(properties))
    lines += ["</Document>", "</kml>", ""]
    return "\n".join(lines)


def with_display_properties(feature):
    properties = dict(feature["properties"])
    style = line_style(properties)
    properties["libelle"] = CATEGORIES[properties["categorie"]]["label"]
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
    outputs = {
        "plougoumelen-mobilites-douces.kml": build_kml("Plougoumelen – mobilités douces", planned + existing),
        "plougoumelen-mobilites-douces.geojson": json.dumps(
            {"type": "FeatureCollection", "features": [with_display_properties(feature) for feature in planned + existing]},
            ensure_ascii=False,
        ),
    }
    layer_summary = []
    for category, style in CATEGORIES.items():
        for status_slug, status_label in STATUSES.items():
            layer_features = [
                feature
                for feature in planned + existing
                if feature["properties"]["categorie"] == category and feature["properties"]["statut"] == status_label
            ]
            if not layer_features:
                continue
            total_length = sum(feature["properties"]["longueur_m"] for feature in layer_features)
            layer_summary.append("  %-12s %-8s %3d tronçons  %6.1f km" % (style["short_label"], status_label, len(layer_features), total_length / 1000))
            file_name = "plougoumelen-mobilites-douces-%s-%s.kml" % (category.replace("_", "-"), status_slug)
            document_name = "Plougoumelen – %s – %s" % (style["short_label"], status_label)
            outputs[file_name] = build_kml(document_name, layer_features)

    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    for stale_file in list(OUTPUT_DIRECTORY.glob("*.kml")) + list(OUTPUT_DIRECTORY.glob("*.geojson")):
        stale_file.unlink()
    for file_name, content in outputs.items():
        (OUTPUT_DIRECTORY / file_name).write_text(content, encoding="utf-8")

    print("OpenStreetMap snapshot: %s" % snapshot_date)
    print("\n".join(layer_summary))
    print("Written %d files to %s" % (len(outputs), OUTPUT_DIRECTORY))


if __name__ == "__main__":
    main()
