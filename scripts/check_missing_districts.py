import psycopg2

ALL_DISTRICTS = [
    "Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler", 
    "Bakırköy", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beykoz", "Beylikdüzü", 
    "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler", "Esenyurt", 
    "Eyüpsultan", "Fatih", "Gaziosmanpaşa", "Güngören", "Kadıköy", "Kağıthane", 
    "Kartal", "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer", 
    "Silivri", "Sultanbeyli", "Sultangazi", "Şile", "Şişli", "Tuzla", 
    "Ümraniye", "Üsküdar", "Zeytinburnu"
]

try:
    conn = psycopg2.connect("dbname=istanbul_gis user=postgres password=123456Qq host=localhost port=5432")
    cur = conn.cursor()
    
    print(f"Checking {len(ALL_DISTRICTS)} districts in osm_istanbul_multipolygons...")
    
    found_count = 0
    missing_districts = []
    
    for district in ALL_DISTRICTS:
        # 1. Tam eşleşme ara (admin_level olmadan)
        cur.execute("SELECT name, admin_level, place FROM osm_istanbul_multipolygons WHERE name ILIKE %s LIMIT 1", (district,))
        row = cur.fetchone()
        
        if row:
            print(f"[FOUND] {district} -> Name: {row[0]}, Level: {row[1]}, Place: {row[2]}")
            found_count += 1
        else:
            # 2. "Belediyesi" ekiyle ara
            cur.execute("SELECT name, admin_level, place FROM osm_istanbul_multipolygons WHERE name ILIKE %s LIMIT 1", (f"{district} Belediyesi",))
            row = cur.fetchone()
            if row:
                print(f"[FOUND-MAPPED] {district} -> Name: {row[0]}, Level: {row[1]}, Place: {row[2]}")
                found_count += 1
            else:
                # 3. İçinde geçiyor mu?
                cur.execute("SELECT name, admin_level, place FROM osm_istanbul_multipolygons WHERE name ILIKE %s LIMIT 1", (f"%{district}%",))
                row = cur.fetchone()
                if row:
                     print(f"[FOUND-PARTIAL] {district} -> Name: {row[0]}, Level: {row[1]}, Place: {row[2]}")
                     found_count += 1
                else:
                    print(f"[MISSING] {district}")
                    missing_districts.append(district)

    print(f"\nSummary: Found {found_count}/{len(ALL_DISTRICTS)}")
    print("Missing:", missing_districts)

    conn.close()
except Exception as e:
    print("Error:", e)
