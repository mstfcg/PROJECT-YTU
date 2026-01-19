import psycopg2
import sys

# Database connection parameters
DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASSWORD = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

# Full list of Marmaray stations (Halkalı to Gebze)
stations = [
    "Halkalı", "Mustafa Kemal", "Küçükçekmece", "Florya", "Florya Akvaryum", 
    "Yeşilköy", "Yeşilyurt", "Ataköy", "Bakırköy", "Yenimahalle", 
    "Zeytinburnu", "Kazlıçeşme", "Yenikapı", "Sirkeci", "Üsküdar", 
    "Ayrılık Çeşmesi", "Söğütlüçeşme", "Feneryolu", "Göztepe", "Erenköy", 
    "Suadiye", "Bostancı", "Küçükyalı", "İdealtepe", "Süreyya Plajı", 
    "Maltepe", "Cevizli", "Atalar", "Başak", "Kartal", 
    "Yunus", "Pendik", "Kaynarca", "Tersane", "Güzelyalı", 
    "Aydıntepe", "İçmeler", "Tuzla", "Çayırova", "Fatih", 
    "Osmangazi", "Darıca", "Gebze"
]

# Hardcoded coordinates for missing or ambiguous stations (Longitude, Latitude)
MISSING_COORDS = {
    "Yenimahalle": (28.8930, 40.9870), 
    "Başak": (29.1860, 40.9030),       
    "Yunus": (29.2200, 40.8950),       
    "Kaynarca": (29.2480, 40.8750),    
    "Tersane": (29.2540, 40.8700),     
    "Güzelyalı": (29.2661, 40.8636),
    "Aydıntepe": (29.2828, 40.8542),
    "Darıca": (29.3875, 40.8167),
    "Pendik": (29.2385, 40.8885),      
    "İçmeler": (29.2970, 40.8480),     
    "Tuzla": (29.3100, 40.8400),       
    "Çayırova": (29.3300, 40.8250),    
    "Fatih": (29.3560, 40.8160),       
    "Osmangazi": (29.3700, 40.8120),   
    "Gebze": (29.4300, 40.8000)        
}

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def seed_marmaray():
    conn = get_db_connection()
    cur = conn.cursor()

    print("Cleaning up existing Marmaray POIs (all cases)...")
    # Clean up both 'marmaray', 'Marmaray', etc.
    cur.execute("DELETE FROM pois WHERE category ILIKE 'marmaray';")
    conn.commit()

    print(f"Seeding {len(stations)} Marmaray stations...")
    
    count = 0
    for station in stations:
        lon, lat = None, None
        
        # Priority 1: Check Hardcoded (Manual Override)
        if station in MISSING_COORDS:
            lon, lat = MISSING_COORDS[station]
            print(f"Using hardcoded coords for {station}: {lon:.4f}, {lat:.4f}")
        else:
            # Priority 2: Check OSM Data (Strict + Tag Check)
            cur.execute("""
                SELECT ST_X(geom), ST_Y(geom) 
                FROM osm_istanbul_points 
                WHERE name ILIKE %s 
                AND (other_tags::text ILIKE '%%railway%%' OR other_tags::text ILIKE '%%public_transport%%')
                LIMIT 1
            """, (station,))
            row = cur.fetchone()
            
            if not row:
                # Priority 3: Check OSM Data (Loose Name Match)
                cur.execute("""
                    SELECT ST_X(geom), ST_Y(geom) 
                    FROM osm_istanbul_points 
                    WHERE name ILIKE %s 
                    LIMIT 1
                """, (station,))
                row = cur.fetchone()

            if row:
                lon, lat = row
                print(f"Found {station} in OSM data: {lon:.4f}, {lat:.4f}")
            else:
                print(f"WARNING: Could not find coordinates for {station}")
                continue

        # Insert into pois as lowercase 'marmaray'
        if lon is not None and lat is not None:
            try:
                insert_sql = """
                    INSERT INTO pois (name, category, geom)
                    VALUES (%s, 'marmaray', ST_SetSRID(ST_MakePoint(%s, %s), 4326));
                """
                cur.execute(insert_sql, (station, lon, lat))
                count += 1
            except Exception as e:
                print(f"Error inserting {station}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nSuccessfully seeded {count} out of {len(stations)} stations.")

if __name__ == "__main__":
    seed_marmaray()
