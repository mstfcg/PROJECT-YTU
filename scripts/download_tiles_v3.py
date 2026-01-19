import os
import requests
import time
import random
import math

# Tiles URL pattern (OpenStreetMap)
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OUTPUT_DIR = "istanbul_ulasim/static/tiles"

# ISTANBUL GENİŞ KAPSAM (Wider Bounds)
# North: Kilyos/Sariyer yukarisi
# South: Tuzla/Adalar asagisi
# West: Buyukcekmece
# East: Gebze siniri/Sabiha Gokcen
BOUNDS = {
    "north": 41.30,
    "south": 40.80,
    "west": 28.50,
    "east": 29.45
}

# Zoom 10: Genel Bakış (Çok az dosya, tüm şehri gösterir)
# Zoom 11: İlçe detayları
# Zoom 12: Mahalle detayları
# Zoom 13: Sokak detayları (Dosya sayısı artar)
ZOOM_LEVELS = [10, 11, 12, 13]

HEADERS = {
    "User-Agent": "IstanbulUlasimOfflineApp/1.0 (Educational Project)"
}

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def download_tile(z, x, y):
    url = TILE_URL.format(z=z, x=x, y=y)
    path = os.path.join(OUTPUT_DIR, str(z), str(x), f"{y}.png")
    
    if os.path.exists(path):
        # 0 byte veya çok küçük hatalı dosyaları yeniden indir
        if os.path.getsize(path) > 100:
            return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            time.sleep(0.05) # Hız sınırı (Rate limit) koruması
        else:
            print(f"Failed: {z}/{x}/{y} -> {response.status_code}")
    except Exception as e:
        print(f"Error {z}/{x}/{y}: {e}")

if __name__ == "__main__":
    print("Harita parçaları hesaplanıyor...")
    tasks = []

    for z in ZOOM_LEVELS:
        top_left = deg2num(BOUNDS["north"], BOUNDS["west"], z)
        bottom_right = deg2num(BOUNDS["south"], BOUNDS["east"], z)
        
        x_start, x_end = top_left[0], bottom_right[0]
        y_start, y_end = top_left[1], bottom_right[1]

        print(f"Zoom {z}: X[{x_start}-{x_end}], Y[{y_start}-{y_end}]")
        
        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                tasks.append((z, x, y))

    print(f"Toplam indirilecek parça sayısı: {len(tasks)}")
    print("İndirme başlıyor... (Bu işlem internet hızına göre 1-2 dakika sürebilir)")
    
    for i, (z, x, y) in enumerate(tasks):
        download_tile(z, x, y)
        if i % 50 == 0:
            print(f"İlerleme: {i}/{len(tasks)}")

    print("İndirme tamamlandı.")
