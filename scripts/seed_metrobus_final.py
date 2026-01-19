import psycopg2

DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASS = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

STATIONS = [
    "Söğütlüçeşme", "Fikirtepe", "Uzunçayır", "Acıbadem", "Altunizade", 
    "Burhaniye", "15 Temmuz Şehitler Köprüsü", "Mecidiyeköy", "Çağlayan", 
    "Okmeydanı Hastane", "Darülaceze - Perpa", "Okmeydanı", "Halıcıoğlu", 
    "Ayvansaray - Eyüp Sultan", "Edirnekapı", "Bayrampaşa - Maltepe", 
    "Topkapı - Şehit Mustafa Cambaz", "Cevizlibağ", "Merter", "Zeytinburnu", 
    "İncirli", "Bahçelievler", "Şirinevler", "Yenibosna", "Sefaköy", 
    "Beşyol", "Florya", "Cennet Mahallesi", "Küçükçekmece", 
    "İBB Sosyal Tesisleri", "Şükrübey", "Avcılar Merkez", 
    "Cihangir - Üniversite Mahallesi", 
    "Saadetdere Mahallesi", "Haramidere Sanayi", "Haramidere", 
    "Güzelyurt", "Beylikdüzü", "Beylikdüzü Belediye", 
    "Cumhuriyet Mahallesi", "Beykent", "Beylikdüzü Sondurak"
]

# Manual coordinates for some difficult ones (approximate if not found)
MANUAL_COORDS = {
    "15 Temmuz Şehitler Köprüsü": (29.033, 41.046), # Bridge location approx
    "Beylikdüzü Sondurak": (28.612, 41.021),
    "Beylikdüzü Son Durak": (28.612, 41.021),
    "Ayvansaray - Eyüp Sultan": (28.948, 41.042),
    "Cihangir - Üniversite Mahallesi": (28.711, 40.976),
    "Beylikdüzü Belediye": (28.643, 41.013),
    "Okmeydanı": (28.965, 41.058),
    "Beylikdüzü": (28.658, 41.016),
    "Beykent": (28.627, 41.018),
    "Söğütlüçeşme": (29.0377008, 40.9916216)
}

STATION_DISTRICTS = {
    "Söğütlüçeşme": "Kadıköy"
}

def seed_metrobus():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Clear existing
    cur.execute("DELETE FROM pois WHERE category = 'metrobus';")
    print("Cleared existing metrobus entries.")

    found_count = 0
    missing = []

    for station in STATIONS:
        # Check manual first
        if station in MANUAL_COORDS:
            print(f"Using manual coords for '{station}'")
            lon, lat = MANUAL_COORDS[station]
        else:
            # Try to find in OSM
            # Strategy: Search for name containing station string
            # Priority: Contains "Metrobüs", then just name match
            
            search_term = station.replace(" - ", "%").replace(" ", "%") # simplistic wildcarding
            
            # Try specific query first
            query = """
                SELECT name, ST_X(geom), ST_Y(geom) 
                FROM osm_istanbul_points 
                WHERE name ILIKE %s 
                ORDER BY 
                    CASE WHEN name ILIKE '%%metrobüs%%' THEN 0 ELSE 1 END,
                    LENGTH(name) ASC
                LIMIT 1;
            """
            cur.execute(query, (f"%{station}%",))
            row = cur.fetchone()

            if row:
                print(f"Found '{station}' as '{row[0]}'")
                lon, lat = row[1], row[2]
            else:
                print(f"MISSING: {station}")
                missing.append(station)
                continue

        # Insert
        insert_sql = """
            INSERT INTO pois (name, category, district, geom)
            VALUES (%s, 'metrobus', %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326));
        """
        cur.execute(insert_sql, (station, STATION_DISTRICTS.get(station), lon, lat))
        found_count += 1

    print(f"\nTotal seeded: {found_count}/{len(STATIONS)}")
    if missing:
        print("Missing stations:")
        for m in missing:
            print(f" - {m}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    seed_metrobus()
