import psycopg2
import os

DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASSWORD = os.environ.get("DB_PASSWORD", "123456Qq")
DB_HOST = "localhost"
DB_PORT = "5432"

def verify():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        cur.execute("SELECT name, ST_X(geom), ST_Y(geom) FROM pois WHERE category = 'marmaray' ORDER BY id")
        rows = cur.fetchall()
        
        print(f"Total Marmaray stations found: {len(rows)}")
        for row in rows:
            print(f"- {row[0]}: ({row[1]}, {row[2]})")
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify()
