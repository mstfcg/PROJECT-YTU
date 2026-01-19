import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASSWORD = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

DEFAULT_GEOJSON_PATH = Path(__file__).resolve().parents[1] / "data" / "Istanbul.osm.geojson"

BATCH_SIZE = 2000
ALLOWED_TOURISM = {"hotel"}


def _collect_coords(coords, out):
    if not coords:
        return
    if isinstance(coords[0], (int, float)):
        out.append(coords)
        return
    for item in coords:
        _collect_coords(item, out)


def _extract_point(geom):
    if not geom:
        return None
    coords = geom.get("coordinates")
    if not coords:
        return None
    points = []
    _collect_coords(coords, points)
    if not points:
        return None
    lon = sum(p[0] for p in points) / len(points)
    lat = sum(p[1] for p in points) / len(points)
    return lon, lat


def _iter_features(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("{\"type\":\"FeatureCollection\""):
                continue
            if line in ("]", "]}", "}"):
                continue
            if line.endswith(","):
                line = line[:-1]
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "Feature":
                continue
            yield obj


def seed_hotels(geojson_path):
    if not geojson_path.exists():
        raise FileNotFoundError(f"GeoJSON not found: {geojson_path}")

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("DELETE FROM pois WHERE category = %s;", ("otel",))

    insert_sql = """
        INSERT INTO pois (name, category, district, geom)
        VALUES %s
    """
    template = "(%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))"

    batch = []
    total = 0

    for feature in _iter_features(geojson_path):
        props = feature.get("properties") or {}
        if props.get("tourism") not in ALLOWED_TOURISM:
            continue

        name = (
            (props.get("name") or "").strip()
            or (props.get("name:tr") or "").strip()
            or (props.get("name:en") or "").strip()
        )
        if not name:
            continue

        point = _extract_point(feature.get("geometry"))
        if not point:
            continue
        lon, lat = point

        district = (
            (props.get("addr:district") or "").strip()
            or (props.get("addr:city") or "").strip()
            or (props.get("addr:neighbourhood") or "").strip()
            or (props.get("addr:suburb") or "").strip()
            or "İstanbul"
        )

        batch.append((name, "otel", district, lon, lat))

        if len(batch) >= BATCH_SIZE:
            execute_values(cur, insert_sql, batch, template=template, page_size=BATCH_SIZE)
            total += len(batch)
            batch.clear()

    if batch:
        execute_values(cur, insert_sql, batch, template=template, page_size=BATCH_SIZE)
        total += len(batch)

    conn.commit()
    cur.close()
    conn.close()
    return total


if __name__ == "__main__":
    path = Path(os.environ.get("OSM_GEOJSON_PATH", DEFAULT_GEOJSON_PATH))
    count = seed_hotels(path)
    print(f"Inserted {count} hotel rows into pois.")
