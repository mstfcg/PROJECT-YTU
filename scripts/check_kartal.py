import psycopg2
try:
    conn = psycopg2.connect("dbname=istanbul_gis user=postgres password=123456Qq host=localhost port=5432")
    cur = conn.cursor()
    # Check if we have Kartal in the multipolygons table
    cur.execute("SELECT name, admin_level FROM osm_istanbul_multipolygons WHERE name ILIKE '%Kartal%'")
    rows = cur.fetchall()
    print("Kartal matches:", rows)
    conn.close()
except Exception as e:
    print("Error:", e)
