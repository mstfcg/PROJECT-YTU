
from pathlib import Path
import sys

import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "istanbul_ulasim"))

DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASSWORD = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

def inspect_data():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        # 1. Coordinates of the specific nodes from previous run
        node_ids = [4583455731, 513620206]
        print(f"Checking nodes: {node_ids}")
        for nid in node_ids:
            cur.execute("SELECT id, ST_Y(geometry::geometry), ST_X(geometry::geometry) FROM nodes_walk WHERE id = %s", (nid,))
            row = cur.fetchone()
            if row:
                print(f"Node {nid}: lat={row[1]}, lon={row[2]}")
            else:
                print(f"Node {nid}: NOT FOUND")

        # 2. Check geocoded coordinates again
        import app
        a = app.geocode_place('Küçükyalı')
        b = app.geocode_place('Küçükyalı Metro')
        print(f"Geocode 'Küçükyalı': {a}")
        print(f"Geocode 'Küçükyalı Metro': {b}")

        # 3. Check distance between nodes
        if a and b:
             cur.execute("SELECT ST_Distance(ST_SetSRID(ST_Point(%s, %s), 4326)::geography, ST_SetSRID(ST_Point(%s, %s), 4326)::geography)", (a[1], a[0], b[1], b[0]))
             dist = cur.fetchone()[0]
             print(f"Distance between geocoded points: {dist} meters")

        # 4. Check edges_walk sample to see cost units
        cur.execute("SELECT cost, ST_Length(geometry::geography) as len_m FROM edges_walk LIMIT 5")
        print("\nChecking edges_walk cost vs length(m):")
        for row in cur.fetchall():
            print(f"Cost: {row[0]}, Length(m): {row[1]}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_data()
