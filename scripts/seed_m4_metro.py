import psycopg2

DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASS = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

STATIONS = [
    "Kadıköy",
    "Ayrılık Çeşmesi",
    "Acıbadem",
    "Ünalan",
    "Göztepe",
    "Yenisahra",
    "Kozyatağı",
    "Bostancı",
    "Küçükyalı",
    "Maltepe",
    "Huzurevi",
    "Gülsuyu",
    "Esenkent",
    "Hastane-Adliye",
    "Soğanlık",
    "Kartal",
    "Yakacık-Adnan Kahveci",
    "Pendik",
    "Tavşantepe",
    "Fevzi Çakmak-Hastane",
    "Yayalar-Şeyhli",
    "Kurtköy",
    "Sabiha Gökçen Havalimanı"
]

# Manual coordinates for stations (using approximate locations for M4 line)
# Source: General knowledge of M4 route (D100 then North to SAW)
MANUAL_COORDS = {
    "Kadıköy": (29.0232, 40.9900), # Near Pier
    "Ayrılık Çeşmesi": (29.0322, 41.0006),
    "Acıbadem": (29.0494, 41.0033),
    "Ünalan": (29.0600, 40.9967),
    "Göztepe": (29.0700, 40.9936),
    "Yenisahra": (29.0883, 40.9856),
    "Kozyatağı": (29.1022, 40.9786),
    "Bostancı": (29.1172, 40.9678), # D100 side
    "Küçükyalı": (29.1283, 40.9578),
    "Maltepe": (29.1417, 40.9497),
    "Huzurevi": (29.1539, 40.9417),
    "Gülsuyu": (29.1672, 40.9328),
    "Esenkent": (29.1806, 40.9239),
    "Hastane-Adliye": (29.1939, 40.9150),
    "Soğanlık": (29.2072, 40.9061),
    "Kartal": (29.2206, 40.8972),
    "Yakacık-Adnan Kahveci": (29.2339, 40.8883),
    "Pendik": (29.2472, 40.8794), # D100 side
    "Tavşantepe": (29.2597, 40.8792),
    "Fevzi Çakmak-Hastane": (29.2711, 40.8878),
    "Yayalar-Şeyhli": (29.2825, 40.8986),
    "Kurtköy": (29.2939, 40.9094),
    "Sabiha Gökçen Havalimanı": (29.311944, 40.906667),
}

def seed_m4_metro():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    conn.autocommit = True
    cur = conn.cursor()

    print("Seeding M4 Metro Line Stations...")
    
    found_count = 0
    missing = []

    for station in STATIONS:
        # 1. Clean up existing entry for this specific station to avoid duplicates
        # We delete by name AND category='metro' to be safe
        cur.execute("DELETE FROM pois WHERE name = %s AND category = 'metro';", (station,))
        
        # 2. Check manual first
        if station in MANUAL_COORDS:
            print(f"Using manual coords for '{station}'")
            lon, lat = MANUAL_COORDS[station]
        else:
            # 3. Try to find in OSM
            # Strategy: Search for name containing station string
            # We replace " - " with "%" to handle spacing differences
            search_term = station.replace("-", "%").replace(" ", "%") 
            
            query = """
                SELECT name, ST_X(geom), ST_Y(geom) 
                FROM osm_istanbul_points 
                WHERE name ILIKE %s 
                ORDER BY 
                    CASE WHEN name ILIKE '%%metro%%' THEN 0 ELSE 1 END,
                    LENGTH(name) ASC
                LIMIT 1;
            """
            cur.execute(query, (f"%{search_term}%",))
            row = cur.fetchone()

            if row:
                print(f"Found '{station}' as '{row[0]}'")
                lon, lat = row[1], row[2]
            else:
                print(f"MISSING: {station}")
                missing.append(station)
                continue

        # 4. Insert
        insert_sql = """
            INSERT INTO pois (name, category, geom)
            VALUES (%s, 'metro', ST_SetSRID(ST_MakePoint(%s, %s), 4326));
        """
        cur.execute(insert_sql, (station, lon, lat))
        found_count += 1

    print(f"\nTotal seeded: {found_count}/{len(STATIONS)}")
    if missing:
        print("Missing stations (need manual coords):")
        for m in missing:
            print(f" - {m}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    seed_m4_metro()
