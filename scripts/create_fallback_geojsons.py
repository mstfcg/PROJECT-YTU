import json
import os

# app.py'den alınan koordinatlar
KNOWN_DISTRICTS = {
    "adalar": (40.8763, 29.0906),
    "arnavutkoy": (41.1848, 28.7408),
    "atasehir": (40.9901, 29.1171),
    "avcilar": (40.9784, 28.7236),
    "bagcilar": (41.0335, 28.8576),
    "bahcelievler": (40.9982, 28.8617),
    "bakirkoy": (40.9782, 28.8744),
    "basaksehir": (41.0969, 28.8077),
    "bayrampasa": (41.0345, 28.9114),
    "besiktas": (41.0422, 29.0067),
    "beykoz": (41.1233, 29.1084),
    "beylikduzu": (41.0024, 28.6436),
    "beyoglu": (41.0284, 28.9736),
    "buyukcekmece": (41.0215, 28.5796),
    "catalca": (41.1436, 28.4608),
    "cekmekoy": (41.0353, 29.1724),
    "esenler": (41.0385, 28.8924),
    "esenyurt": (41.0343, 28.6801),
    "eyupsultan": (41.0475, 28.9329),
    "fatih": (41.0115, 28.9349),
    "gaziosmanpasa": (41.0573, 28.9103),
    "gungoren": (41.0223, 28.8727),
    "kadikoy": (40.9819, 29.0254),
    "kagithane": (41.0805, 28.9780),
    "kartal": (40.8906, 29.1925),
    "kucukcekmece": (40.9918, 28.7712),
    "maltepe": (40.9257, 29.1325),
    "pendik": (40.8769, 29.2346),
    "sancaktepe": (40.9904, 29.2274),
    "sariyer": (41.1664, 29.0504),
    "silivri": (41.0742, 28.2482),
    "sultanbeyli": (40.9678, 29.2612),
    "sultangazi": (41.1093, 28.8661),
    "sile": (41.1744, 29.6125),
    "sisli": (41.0530, 28.9877),
    "tuzla": (40.8166, 29.3033),
    "umraniye": (41.0256, 29.0963),
    "uskudar": (41.0260, 29.0168),
    "zeytinburnu": (40.9897, 28.9038)
}

OUTPUT_DIR = r"c:\Users\PC\Desktop\PROJECT-YTU\istanbul_ulasim\static\geojson"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Yarıçap (derece cinsinden, yaklaşık 3-4km)
DELTA = 0.035 

print(f"Generating GeoJSONs for {len(KNOWN_DISTRICTS)} districts...")

for name, coords in KNOWN_DISTRICTS.items():
    lat, lon = coords
    
    # Basit bir kare oluştur (Bounding Box)
    # [min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat], [min_lon, max_lat], [min_lon, min_lat]
    min_lat = lat - DELTA
    max_lat = lat + DELTA
    min_lon = lon - DELTA * 1.3 # Boylam aralığını enlemden biraz daha geniş tut (Türkiye enlemi için)
    max_lon = lon + DELTA * 1.3
    
    geojson_content = {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "properties": {
            "name": name.capitalize()
          },
          "geometry": {
            "type": "Polygon",
            "coordinates": [
              [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat]
              ]
            ]
          }
        }
      ]
    }
    
    # Dosya adı (zaten normalized key kullanıyoruz)
    file_path = os.path.join(OUTPUT_DIR, f"{name}.json")
    
    # Eğer dosya zaten varsa ve boyutu büyükse (yani gerçek veri ise) üzerine yazma!
    # Ama şu anki dosyalarım yok veya test amaçlı, hepsini oluşturuyorum.
    # Sadece Kartal'ı elimle oluşturmuştum, onu koruyabilirim ama bu daha genel.
    # Kartal'ı da bu standart kare ile değiştirmek daha tutarlı olabilir, 
    # veya eğer daha detaylıysa kalsın. Kartal.json'un boyutu küçükse (kare ise) üzerine yaz.
    
    should_write = True
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        if size > 2000: # Eğer 2KB'dan büyükse muhtemelen gerçek sınırdır, dokunma
            print(f"Skipping {name} (existing file seems detailed: {size} bytes)")
            should_write = False
            
    if should_write:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(geojson_content, f, indent=2)
        print(f"Created {name}.json")

print("Done.")
