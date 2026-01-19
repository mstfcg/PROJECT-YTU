import psycopg2

try:
    conn = psycopg2.connect("dbname=istanbul_gis user=postgres password=123456Qq host=localhost port=5432")
    cur = conn.cursor()
    
    print("Checking for districts (admin_level='6')...")
    cur.execute("SELECT name, admin_level FROM osm_istanbul_multipolygons WHERE admin_level='6'")
    rows = cur.fetchall()
    
    if rows:
        print(f"Found {len(rows)} districts:")
        for row in rows:
            print(f" - {row[0]}")
    else:
        print("No districts with admin_level='6' found.")

    print("\nChecking for anything containing 'Kartal' in multipolygons (limit 20)...")
    cur.execute("SELECT name, admin_level, place FROM osm_istanbul_multipolygons WHERE name ILIKE '%Kartal%' LIMIT 20")
    kartal_rows = cur.fetchall()
    for row in kartal_rows:
        print(f" - Name: {row[0]}, Admin Level: {row[1]}, Place: {row[2] if len(row) > 2 else 'N/A'}")

    conn.close()
except Exception as e:
    print("Error:", e)
