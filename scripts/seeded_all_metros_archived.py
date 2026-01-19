import psycopg2

DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASS = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

# Station Lists
LINES = {
    "metro-m1a": [
        "Yenikapı", "Aksaray", "Emniyet - Fatih", "Topkapı - Ulubatlı", 
        "Bayrampaşa - Maltepe", "Sağmalcılar", "Kocatepe", "Otogar", 
        "Terazidere", "Davutpaşa - YTÜ", "Merter", "Zeytinburnu", 
        "Bakırköy - İncirli", "Bahçelievler", "Ataköy - Şirinevler", 
        "Yenibosna", "DTM - İstanbul Fuar Merkezi", "Atatürk Havalimanı"
    ],
    "metro-m1b": [
        "Yenikapı", "Aksaray", "Emniyet - Fatih", "Topkapı - Ulubatlı", 
        "Bayrampaşa - Maltepe", "Sağmalcılar", "Kocatepe", "Otogar",
        "Esenler", "Menderes", "Üçyüzlü", "Bağcılar Meydan", "Kirazlı - Bağcılar"
    ],
    "metro-m2": [
        "Yenikapı", "Vezneciler - İstanbul Üniversitesi", "Haliç", "Şişhane", 
        "Taksim", "Osmanbey", "Şişli - Mecidiyeköy", "Gayrettepe", "Levent", 
        "4. Levent", "Sanayi Mahallesi", "Seyrantepe", "İTÜ - Ayazağa", 
        "Atatürk Oto Sanayi", "Darüşşafaka", "Hacıosman"
    ],
    "metro-m3": [
        "Bakırköy Sahil", "Özgürlük Meydanı", "İncirli", "Haznedar", "İlkyuva",
        "Yıldıztepe", "Molla Gürani", "Kirazlı - Bağcılar", "Yenimahalle", 
        "Mahmutbey", "İSTOÇ", "İkitelli Sanayi", "Turgut Özal", "Siteler", 
        "Başak Konutları", "Metrokent", "Onurkent", "Şehir Hastanesi", "Kayaşehir Merkez"
    ],
    "metro-m4": [
        "Kadıköy", "Ayrılık Çeşmesi", "Acıbadem", "Ünalan", "Göztepe", 
        "Yenisahra", "Kozyatağı", "Bostancı", "Küçükyalı", "Maltepe", 
        "Huzurevi", "Gülsuyu", "Esenkent", "Hastane - Adliye", "Soğanlık", 
        "Kartal", "Yakacık - Adnan Kahveci", "Pendik", "Tavşantepe", 
        "Fevzi Çakmak - Hastane", "Yayalar - Şeyhli", "Kurtköy", "Sabiha Gökçen Havalimanı"
    ],
    "metro-m5": [
        "Üsküdar", "Fıstıkağacı", "Bağlarbaşı", "Altunizade", "Kısıklı", 
        "Bulgurlu", "Ümraniye", "Çarşı", "Yamanevler", "Çakmak", "Ihlamurkuyu", 
        "Altınşehir", "İmam Hatip Lisesi", "Dudullu", "Necip Fazıl", "Çekmeköy", 
        "Meclis", "Sarıgazi", "Sancaktepe", "Sancaktepe Şehir Hastanesi", "Samandıra Merkez"
    ],
    "metro-m6": [
        "Levent", "Nispetiye", "Etiler", "Boğaziçi Üniversitesi - Hisarüstü"
    ],
    "metro-m7": [
        "Yıldız", "Fulya", "Mecidiyeköy", "Çağlayan", "Kağıthane", "Nurtepe", 
        "Alibeyköy", "Çırçır", "Veysel Karani - Akşemsettin", "Yeşilpınar", 
        "Kazım Karabekir", "Yenimahalle", "Karadeniz Mahallesi", 
        "Tekstilkent - Giyimkent", "Oruç Reis", "Göztepe Mahallesi", "Mahmutbey"
    ],
    "metro-m8": [
        "Bostancı", "Emin Ali Paşa", "Ayşekadın", "Kozyatağı", "Küçükbakkalköy", 
        "İçerenköy", "Kayışdağı", "Mevlana", "İmes", "Modoko - Keyap", 
        "Dudullu", "Huzur", "Parseller"
    ],
    "metro-m9": [
        "Ataköy", "Yenibosna", "Çobançeşme", "29 Ekim Cumhuriyet", "Doğu Sanayi", 
        "Mimar Sinan", "15 Temmuz", "Halkalı Caddesi", "Atatürk Mahallesi", 
        "Bahariye", "MASKO", "İkitelli Sanayi", "Ziya Gökalp", "Olimpiyat"
    ],
    "metro-m11": [
        "Gayrettepe", "Kağıthane", "Hasdal", "Kemerburgaz", "Göktürk", 
        "İhsaniye", "İstanbul Havalimanı", "Kargo Terminali", "Taşoluk", "Arnavutköy"
    ]
}

# Manual Coordinates (Fallbacks for OSM misses or ambiguities)
# Format: "Station Name": (Lon, Lat)
MANUAL_COORDS = {
    # M4
    "Kadıköy": (29.0232, 40.9900),
    "Ayrılık Çeşmesi": (29.0322, 41.0006),
    "Acıbadem": (29.0494, 41.0033),
    "Ünalan": (29.0600, 40.9967),
    "Göztepe": (29.0700, 40.9936),
    "Yenisahra": (29.0883, 40.9856),
    "Kozyatağı": (29.1022, 40.9786),
    "Bostancı": (29.1172, 40.9678), 
    "Küçükyalı": (29.1283, 40.9578),
    "Maltepe": (29.1417, 40.9497),
    "Huzurevi": (29.1539, 40.9417),
    "Gülsuyu": (29.1672, 40.9328),
    "Esenkent": (29.1806, 40.9239),
    "Hastane - Adliye": (29.1939, 40.9150),
    "Soğanlık": (29.2072, 40.9061),
    "Kartal": (29.2206, 40.8972),
    "Yakacık - Adnan Kahveci": (29.2339, 40.8883),
    "Pendik": (29.2472, 40.8794), 
    "Tavşantepe": (29.2597, 40.8792),
    "Fevzi Çakmak - Hastane": (29.2711, 40.8878),
    "Yayalar - Şeyhli": (29.2825, 40.8986),
    "Kurtköy": (29.2939, 40.9094),
    "Sabiha Gökçen Havalimanı": (29.311944, 40.906667),
    
    # M11
    "İstanbul Havalimanı": (28.7420, 41.2580),
    "Gayrettepe": (29.0064, 41.0664),
    "Kağıthane": (28.9710, 41.0790),
    "Göktürk": (28.8920, 41.1680),
    "Kemerburgaz": (28.9150, 41.1440),

    # M3 Extensions
    "Bakırköy Sahil": (28.8744, 40.9769),
    "Özgürlük Meydanı": (28.8741, 40.9816),
    "İncirli": (28.8686, 40.9967),
    "Yıldıztepe": (28.8647, 41.0203),
    "Molla Gürani": (28.8644, 41.0319),
    "Şehir Hastanesi": (28.7772, 41.1032),
    "Kayaşehir Merkez": (28.7666, 41.1066),
    
    # M9
    "Ataköy": (28.8475, 40.9847),
    "Çobançeşme": (28.8350, 41.0028),
    "29 Ekim Cumhuriyet": (28.8256, 41.0119),
    "Doğu Sanayi": (28.8189, 41.0206),
    
    # Shared / Ambiguous
    "Yenikapı": (28.9516, 41.0052),
    "Kirazlı - Bağcılar": (28.8450, 41.0336),
    "Mahmutbey": (28.8333, 41.0558),
    "Mecidiyeköy": (28.9933, 41.0656),
    "Şişli - Mecidiyeköy": (28.9933, 41.0656),
    "Üsküdar": (29.0131, 41.0256),
    "Altunizade": (29.0430, 41.0230),
    
    # M5 Extension
    "Samandıra Merkez": (29.2314, 40.9837),
    "Sancaktepe": (29.2290, 40.9921),
    "Sarıgazi": (29.2127, 41.0100),
    "Meclis": (29.1983, 41.0136),
    "Çekmeköy": (29.1867, 41.0169),
    "Necip Fazıl": (29.1779, 41.0168),
    
    # M8
    "Parseller": (29.1527, 41.0312),
    "Huzur": (29.1561, 41.0211),
    "Modoko - Keyap": (29.1622, 41.0069),
    "İmes": (29.1633, 40.9961),
    "Mevlana": (29.1558, 40.9856),
    "Kayışdağı": (29.1417, 40.9825),
    "İçerenköy": (29.1239, 40.9758),
    "Küçükbakkalköy": (29.1128, 40.9750),
    "Ayşekadın": (29.0967, 40.9669),
    "Emin Ali Paşa": (29.0922, 40.9619),
    
    # M7
    "Yıldız": (29.0097, 41.0541),
    "Fulya": (29.0017, 41.0583),
}

def seed_all_metros():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    conn.autocommit = True
    cur = conn.cursor()

    print("--- Cleaning up old Metro entries ---")
    # Delete all categories starting with 'metro' (including 'metro-m1a', 'metro', etc.)
    # Be careful not to delete 'metrobus' if it starts with 'metro' -> 'metro%' matches metrobus too!
    # 'metrobus' starts with 'metro'. So 'metro%' deletes metrobus.
    # We should delete 'metro' and 'metro-%'.
    cur.execute("DELETE FROM pois WHERE category = 'metro' OR category LIKE 'metro-%';")
    print("Deleted old metro entries (kept metrobus).")

    total_added = 0
    
    for line_code, stations in LINES.items():
        print(f"\nProcessing {line_code} ({len(stations)} stations)...")
        for station in stations:
            # Clean name for search
            clean_name = station.split(" - ")[0] # Take first part for search if dashed
            
            lon, lat = None, None
            
            # 1. Manual check (Full name)
            if station in MANUAL_COORDS:
                lon, lat = MANUAL_COORDS[station]
            # 2. Manual check (Clean name)
            elif clean_name in MANUAL_COORDS:
                lon, lat = MANUAL_COORDS[clean_name]
            else:
                # 3. OSM Search
                # Try full name first
                search_term = station.replace(" - ", "%").replace(" ", "%")
                query = """
                    SELECT ST_X(geom), ST_Y(geom) 
                    FROM osm_istanbul_points 
                    WHERE name ILIKE %s 
                    ORDER BY 
                        CASE WHEN name ILIKE '%%metro%%' THEN 0 ELSE 1 END,
                        LENGTH(name) ASC
                    LIMIT 1;
                """
                cur.execute(query, (f"%{search_term}%",))
                row = cur.fetchone()
                
                if not row:
                    # Try clean name
                    cur.execute(query, (f"%{clean_name}%",))
                    row = cur.fetchone()
                
                if row:
                    lon, lat = row[0], row[1]
                else:
                    print(f"  [WARN] Could not find coords for '{station}'. Skipping.")
                    continue
            
            if lon and lat:
                # Insert
                insert_sql = """
                    INSERT INTO pois (name, category, geom, district)
                    VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), 'Istanbul');
                """
                # We don't have district easily, set to Istanbul or update later via spatial join if needed.
                # For now 'Istanbul' is fine or we can omit district.
                cur.execute(insert_sql, (station, line_code, lon, lat))
                total_added += 1
                # print(f"  Added {station}")

    print(f"\nTotal stations seeded: {total_added}")
    
    # Optional: Update districts spatially
    print("Updating districts from polygons...")
    cur.execute("""
        UPDATE pois
        SET district = d.name
        FROM districts d
        WHERE pois.category LIKE 'metro-%' 
          AND ST_Contains(d.geom, pois.geom);
    """)
    print("Districts updated.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    seed_all_metros()
