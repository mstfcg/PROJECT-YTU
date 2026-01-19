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


def _build_full_address(props):
    full_addr = (props.get("addr:full") or "").strip()
    if full_addr:
        return full_addr

    street = (props.get("addr:street") or "").strip()
    house_number = (props.get("addr:housenumber") or "").strip()
    neighbourhood = (props.get("addr:neighbourhood") or "").strip()
    district = (props.get("addr:district") or "").strip()
    city = (props.get("addr:city") or "").strip()
    postcode = (props.get("addr:postcode") or "").strip()

    parts = []
    if street and house_number:
        parts.append(f"{street} {house_number}")
    elif street:
        parts.append(street)
    elif house_number:
        parts.append(house_number)
    if neighbourhood:
        parts.append(neighbourhood)
    if district:
        parts.append(district)
    if city:
        parts.append(city)
    if postcode:
        parts.append(postcode)
    return ", ".join([p for p in parts if p]) if parts else None


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


def build_osm_addresses(geojson_path):
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

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS osm_addresses (
            id BIGSERIAL PRIMARY KEY,
            geom geometry(Point, 4326),
            name text,
            house_number text,
            street text,
            neighbourhood text,
            district text,
            city text,
            postcode text,
            full_address text,
            source text
        );
        """
    )
    cur.execute("TRUNCATE osm_addresses;")

    insert_sql = """
        INSERT INTO osm_addresses (
            geom,
            name,
            house_number,
            street,
            neighbourhood,
            district,
            city,
            postcode,
            full_address,
            source
        ) VALUES %s
    """
    template = (
        "(ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )

    batch = []
    total = 0

    for feature in _iter_features(geojson_path):
        props = feature.get("properties") or {}
        if not any(
            props.get(k)
            for k in (
                "addr:street",
                "addr:housenumber",
                "addr:neighbourhood",
                "addr:district",
                "addr:city",
                "addr:postcode",
                "addr:full",
            )
        ):
            continue

        point = _extract_point(feature.get("geometry"))
        if not point:
            continue
        lon, lat = point

        name = (props.get("name") or props.get("addr:housename") or "").strip() or None
        house_number = (props.get("addr:housenumber") or "").strip() or None
        street = (props.get("addr:street") or "").strip() or None
        neighbourhood = (props.get("addr:neighbourhood") or "").strip() or None
        district = (props.get("addr:district") or "").strip() or None
        city = (props.get("addr:city") or "").strip() or None
        postcode = (props.get("addr:postcode") or "").strip() or None
        full_address = _build_full_address(props)

        batch.append(
            (
                lon,
                lat,
                name,
                house_number,
                street,
                neighbourhood,
                district,
                city,
                postcode,
                full_address,
                "geojson",
            )
        )

        if len(batch) >= BATCH_SIZE:
            execute_values(cur, insert_sql, batch, template=template, page_size=BATCH_SIZE)
            total += len(batch)
            batch.clear()

    if batch:
        execute_values(cur, insert_sql, batch, template=template, page_size=BATCH_SIZE)
        total += len(batch)

    cur.execute(
        "CREATE INDEX IF NOT EXISTS osm_addresses_geom_gix ON osm_addresses USING GIST (geom);"
    )
    conn.commit()
    cur.close()
    conn.close()
    return total


if __name__ == "__main__":
    path = Path(os.environ.get("OSM_GEOJSON_PATH", DEFAULT_GEOJSON_PATH))
    count = build_osm_addresses(path)
    print(f"Inserted {count} address rows into osm_addresses.")
