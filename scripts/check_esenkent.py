import psycopg2
import os

DB_HOST = "localhost"
DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASS = "123456Qq"

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)

def check_esenkent():
    conn = get_db_connection()
    cur = conn.cursor()
    # POIS tablosu kontrolü
    print("--- Checking POIS table ---")
    cur.execute("SELECT name, district, ST_AsText(geom) FROM pois WHERE name ILIKE '%Esenkent%' LIMIT 5")
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"POIS: {r}")
    else:
        print("POIS: No match found for Esenkent")

    # OSM_POINTS tablosu kontrolü (varsa)
    print("\n--- Checking OSM_POINTS table ---")
    try:
        cur.execute("SELECT name, ST_AsText(geom) FROM osm_points WHERE name ILIKE '%Esenkent%' LIMIT 5")
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"OSM_POINTS: {r}")
        else:
            print("OSM_POINTS: No match found for Esenkent")
    except Exception as e:
        print(f"OSM_POINTS table check failed: {e}")
        conn.rollback()

    conn.close()

if __name__ == "__main__":
    check_esenkent()
