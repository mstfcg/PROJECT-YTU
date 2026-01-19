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
    
    print(f"Searching for best matches for {len(ALL_DISTRICTS)} districts based on AREA size...")
    
    results_map = {}
    
    for district in ALL_DISTRICTS:
        # Alanına göre en büyük 3 sonucu getir
        # ST_Area(geography(wkb_geometry)) metrekare cinsinden yaklaşık alan verir
        query = """
            SELECT name, admin_level, place, ST_Area(wkb_geometry) as area
            FROM osm_istanbul_multipolygons 
            WHERE name ILIKE %s
            ORDER BY ST_Area(wkb_geometry) DESC 
            LIMIT 3
        """
        cur.execute(query, (f"%{district}%",))
        rows = cur.fetchall()
        
        if rows:
            best_match = rows[0]
            print(f"\n[{district}]")
            for i, row in enumerate(rows):
                print(f"  {i+1}. Name: {row[0]}, Level: {row[1]}, Place: {row[2]}, Area: {row[3]}")
            
            # Eğer en büyük alan belli bir eşiğin üzerindeyse (örn. 0.001 derece kare veya benzeri) kabul edelim
            # Derece kare cinsinden alan küçük görünür (0.01 ~ 100km2 gibi)
            if best_match[3] > 0.0005: # Çok kaba bir eşik, kontrol edeceğiz
                results_map[district] = best_match[0]
        else:
            print(f"\n[{district}] - NO MATCH FOUND")

    print("\nSuggested Mapping:")
    print("DISTRICT_NAME_MAPPING = {")
    for k, v in results_map.items():
        if k != v: # Sadece isim farklıysa ekle
            print(f'    "{k}": "{v}",')
    print("}")

    conn.close()
except Exception as e:
    print("Error:", e)
