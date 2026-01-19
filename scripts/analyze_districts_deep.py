import psycopg2

TARGET_DISTRICTS = [
    "Arnavutköy", "Adalar", "Beykoz", "Beylikdüzü", "Büyükçekmece", 
    "Çatalca", "Çekmeköy", "Eyüpsultan", "Kartal", "Küçükçekmece", 
    "Pendik", "Silivri", "Şile", "Tuzla", "Üsküdar"
]

try:
    conn = psycopg2.connect("dbname=istanbul_gis user=postgres password=123456Qq host=localhost port=5432")
    cur = conn.cursor()
    
    print(f"Deep analyzing {len(TARGET_DISTRICTS)} districts in DB...")
    
    for district in TARGET_DISTRICTS:
        print(f"\n--- {district} ---")
        
        # 1. İsme göre en büyük alanlı kayıtları getir
        query = """
            SELECT name, admin_level, place, ST_Area(wkb_geometry) as area
            FROM osm_istanbul_multipolygons 
            WHERE name ILIKE %s
            ORDER BY ST_Area(wkb_geometry) DESC 
            LIMIT 5
        """
        cur.execute(query, (f"%{district}%",))
        rows = cur.fetchall()
        
        if rows:
            for i, row in enumerate(rows):
                # Alanı okunabilir formata çevir (yaklaşık derece kare)
                area = row[3]
                print(f"  {i+1}. {row[0]} (Level: {row[1]}, Place: {row[2]}) - Area: {area:.6f}")
        else:
            print("  No match found.")

    conn.close()
except Exception as e:
    print("Error:", e)
