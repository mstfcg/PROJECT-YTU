
import psycopg2

DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASSWORD = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

def inspect_osm_table():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'osm_istanbul_points';")
        rows = cur.fetchall()
        for row in rows:
            print(row)
        conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    inspect_osm_table()
