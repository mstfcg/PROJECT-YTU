import json
import os
from pathlib import Path

import psycopg2

DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASSWORD = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

DEFAULT_MAX_DISTANCE_M = 1500
UPDATE_ALL = os.environ.get("UPDATE_ALL", "").strip().lower() in {"1", "true", "yes"}
TRANSLATE_MAP = {
    "ı": "i",
    "İ": "i",
    "I": "i",
    "ğ": "g",
    "Ğ": "g",
    "ü": "u",
    "Ü": "u",
    "ş": "s",
    "Ş": "s",
    "ö": "o",
    "Ö": "o",
    "ç": "c",
    "Ç": "c",
}

OVERRIDES_PATH = Path(__file__).resolve().parents[1] / "data" / "poi_district_overrides.json"

DISTRICT_NAME_MAP = {
    "adalar": "Adalar",
    "arnavutkoy": "Arnavutköy",
    "atasehir": "Ataşehir",
    "avcilar": "Avcılar",
    "bagcilar": "Bağcılar",
    "bahcelievler": "Bahçelievler",
    "bakirkoy": "Bakırköy",
    "basaksehir": "Başakşehir",
    "bayrampasa": "Bayrampaşa",
    "besiktas": "Beşiktaş",
    "beykoz": "Beykoz",
    "beylikduzu": "Beylikdüzü",
    "beyoglu": "Beyoğlu",
    "buyukcekmece": "Büyükçekmece",
    "catalca": "Çatalca",
    "cekmekoy": "Çekmeköy",
    "esenler": "Esenler",
    "esenyurt": "Esenyurt",
    "eyupsultan": "Eyüpsultan",
    "fatih": "Fatih",
    "gaziosmanpasa": "Gaziosmanpaşa",
    "gungoren": "Güngören",
    "kadikoy": "Kadıköy",
    "kagithane": "Kağıthane",
    "kartal": "Kartal",
    "kucukcekmece": "Küçükçekmece",
    "maltepe": "Maltepe",
    "pendik": "Pendik",
    "sancaktepe": "Sancaktepe",
    "sariyer": "Sarıyer",
    "silivri": "Silivri",
    "sultanbeyli": "Sultanbeyli",
    "sultangazi": "Sultangazi",
    "sile": "Şile",
    "sisli": "Şişli",
    "tuzla": "Tuzla",
    "umraniye": "Ümraniye",
    "uskudar": "Üsküdar",
    "zeytinburnu": "Zeytinburnu",
}


def load_overrides(path: Path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Override file error: {exc}")
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        category = (item.get("category") or "").strip().lower()
        name_norm = (item.get("name_norm") or "").strip().lower()
        district_norm = (item.get("district_norm") or "").strip().lower()
        if not category or not name_norm or not district_norm:
            continue
        out.append({
            "category": category,
            "name": (item.get("name") or "").strip(),
            "name_norm": name_norm,
            "district_norm": district_norm,
            "lat": item.get("lat"),
            "lon": item.get("lon"),
        })
    return out


def normalize_name(value):
    if not value:
        return ""
    norm = value.strip().lower()
    for src, dst in TRANSLATE_MAP.items():
        norm = norm.replace(src, dst)
    return " ".join(norm.split())


def apply_overrides(cur, overrides):
    updated = 0
    inserted = 0
    categories = sorted({item["category"] for item in overrides})
    if categories:
        cur.execute(
            "SELECT id, name, category FROM pois WHERE category = ANY(%s);",
            (categories,),
        )
        rows = cur.fetchall()
    else:
        rows = []
    index = {}
    for poi_id, name, category in rows:
        key = (category, normalize_name(name))
        index.setdefault(key, []).append(poi_id)

    for item in overrides:
        district_display = DISTRICT_NAME_MAP.get(
            item["district_norm"], item["district_norm"].title()
        )
        name_norm = normalize_name(item["name_norm"])
        ids = index.get((item["category"], name_norm), [])
        if ids:
            cur.execute(
                "UPDATE pois SET district = %s WHERE id = ANY(%s);",
                (district_display, ids),
            )
            updated += len(ids)
            continue

        if item.get("lat") is None or item.get("lon") is None:
            continue

        name_display = item["name"] or item["name_norm"]
        cur.execute(
            """
            INSERT INTO pois (name, category, district, geom)
            VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326));
            """,
            (
                name_display,
                item["category"],
                district_display,
                item["lon"],
                item["lat"],
            ),
        )
        inserted += 1
    return updated, inserted


def update_missing_districts(max_distance_m, update_all=False):
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT to_regclass('public.osm_istanbul_multipolygons');")
    has_boundaries = cur.fetchone()[0] is not None

    cur.execute("SELECT to_regclass('public.osm_addresses');")
    has_addresses = cur.fetchone()[0] is not None

    if has_boundaries:
        where_clause = "" if update_all else "AND (p.district IS NULL OR BTRIM(p.district) = '')"
        cur.execute(
            f"""
            UPDATE pois p
            SET district = mp.name
            FROM osm_istanbul_multipolygons mp
            WHERE mp.admin_level = '6'
              AND ST_Covers(mp.wkb_geometry, p.geom)
              {where_clause}
            RETURNING p.id;
            """
        )
        updated_from_boundaries = cur.rowcount
    else:
        updated_from_boundaries = 0

    if has_boundaries:
        cur.execute(
            """
            WITH candidates AS (
                SELECT
                    p.id,
                    mp.name AS district,
                    mp.wkb_geometry AS geom
                FROM pois p
                JOIN LATERAL (
                    SELECT name, wkb_geometry
                    FROM osm_istanbul_multipolygons
                    WHERE admin_level = '6'
                    ORDER BY wkb_geometry <-> p.geom
                    LIMIT 1
                ) mp ON TRUE
                WHERE p.district IS NULL OR BTRIM(p.district) = ''
            )
            UPDATE pois p
            SET district = c.district
            FROM candidates c
            WHERE p.id = c.id
              AND ST_DWithin(p.geom::geography, c.geom::geography, %s)
            RETURNING p.id;
            """,
            (max_distance_m,),
        )
        updated_from_nearest_boundary = cur.rowcount
    else:
        updated_from_nearest_boundary = 0

    if has_addresses:
        cur.execute(
            """
            WITH candidates AS (
                SELECT
                    p.id,
                    NULLIF(BTRIM(a.district), '') AS district
                FROM pois p
                JOIN LATERAL (
                    SELECT district, geom
                    FROM osm_addresses
                    WHERE NULLIF(BTRIM(district), '') IS NOT NULL
                      AND ST_DWithin(
                          geom::geography,
                          p.geom::geography,
                          %s
                      )
                    ORDER BY geom <-> p.geom
                    LIMIT 1
                ) a ON TRUE
                WHERE p.district IS NULL OR BTRIM(p.district) = ''
            )
            UPDATE pois p
            SET district = c.district
            FROM candidates c
            WHERE p.id = c.id
            RETURNING p.id;
            """,
            (max_distance_m,),
        )
        updated_from_addresses = cur.rowcount
    else:
        updated_from_addresses = 0

    cur.execute(
        """
        WITH candidates AS (
            SELECT
                p.id,
                NULLIF(BTRIM(n.district), '') AS district
            FROM pois p
            JOIN LATERAL (
                SELECT district, geom
                FROM pois
                WHERE id <> p.id
                  AND NULLIF(BTRIM(district), '') IS NOT NULL
                  AND ST_DWithin(
                      geom::geography,
                      p.geom::geography,
                      %s
                  )
                ORDER BY geom <-> p.geom
                LIMIT 1
            ) n ON TRUE
            WHERE p.district IS NULL OR BTRIM(p.district) = ''
        )
        UPDATE pois p
        SET district = c.district
        FROM candidates c
        WHERE p.id = c.id
        RETURNING p.id;
        """,
        (max_distance_m,),
    )
    updated_from_pois = cur.rowcount

    overrides = load_overrides(OVERRIDES_PATH)
    overrides_updated = 0
    overrides_inserted = 0
    if overrides:
        overrides_updated, overrides_inserted = apply_overrides(cur, overrides)
    conn.commit()
    cur.close()
    conn.close()
    return (
        updated_from_boundaries,
        updated_from_nearest_boundary,
        updated_from_addresses,
        updated_from_pois,
        overrides_updated,
        overrides_inserted,
    )


if __name__ == "__main__":
    max_distance = float(os.environ.get("MAX_DISTANCE_M", DEFAULT_MAX_DISTANCE_M))
    (
        boundary_count,
        nearest_boundary_count,
        addr_count,
        poi_count,
        overrides_updated,
        overrides_inserted,
    ) = update_missing_districts(max_distance, update_all=UPDATE_ALL)
    print(
        "Updated "
        f"{boundary_count} from boundaries, "
        f"{nearest_boundary_count} from nearest boundary, "
        f"{addr_count} from osm_addresses, "
        f"{poi_count} from nearby pois, "
        f"{overrides_updated} overrides, "
        f"{overrides_inserted} inserts."
    )
