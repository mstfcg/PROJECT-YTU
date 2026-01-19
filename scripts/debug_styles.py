
from pathlib import Path
import sys

import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "istanbul_ulasim"))

from app import CAT_STYLES, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

def debug_flow():
    print("--- DEBUGGING CAT_STYLES ---")
    if "havalimani" in CAT_STYLES:
        print(f"CAT_STYLES['havalimani']: {CAT_STYLES['havalimani']}")
    else:
        print("ERROR: 'havalimani' NOT IN CAT_STYLES keys!")
        print(f"Keys: {list(CAT_STYLES.keys())}")

    print("\n--- SIMULATING DB FETCH ---")
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        with conn.cursor() as cur:
            # Simulate fetching airports
            cur.execute("SELECT name, category, ST_AsText(geom) AS wkt FROM pois WHERE category ILIKE '%havalimani%' LIMIT 3")
            rows = cur.fetchall()
            
            results = []
            for r in rows:
                nm, cat, wkt = r
                print(f"Raw from DB: name='{nm}', cat='{cat}'")
                
                # Normalization Logic (Copied from app.py)
                if isinstance(cat, str):
                    cat = cat.strip().lower()
                    if cat == "havalimanı" or cat == "airport":
                        cat = "havalimani"
                    elif cat == "metrobüs":
                        cat = "metrobus"
                    elif cat == "üniversite":
                        cat = "universite"
                    elif cat == "otobüs" or cat == "otobüs durağı":
                        cat = "otobus"
                    elif cat == "vapur iskelesi":
                        cat = "vapur"
                
                print(f"Normalized cat: '{cat}'")
                
                style = CAT_STYLES.get(cat, {"color": "gray", "icon": "info", "prefix": "fa"})
                print(f"Resolved Style: {style}")
                
                if style['icon'] == 'info':
                    print("!!! ALERT: Fallback to default info icon !!!")
                else:
                    print(">>> SUCCESS: Icon is correct")
                print("-" * 30)

    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    debug_flow()
