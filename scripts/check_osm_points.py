import psycopg2

DB_HOST = "localhost"
DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASS = "123456Qq"

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conn

def check_osm_points():
    conn = get_db_connection()
    cur = conn.cursor()
    print("Checking osm_istanbul_points for 'Esenkent'...")
    cur.execute("SELECT name, ST_AsText(geom) FROM osm_istanbul_points WHERE name ILIKE '%Esenkent%' LIMIT 10")
    rows = cur.fetchall()
    for r in rows:
        print(r)
    conn.close()

if __name__ == "__main__":
    check_osm_points()
