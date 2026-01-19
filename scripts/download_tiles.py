import math
import os
import requests
import time

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def download_tiles(zoom_min, zoom_max, lat_min, lat_max, lon_min, lon_max, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    total_tiles = 0
    downloaded_tiles = 0
    
    print(f"Hedef Klasör: {output_dir}")
    print(f"Zoom Aralığı: {zoom_min}-{zoom_max}")
    print(f"Koordinatlar: Lat({lat_min}-{lat_max}), Lon({lon_min}-{lon_max})")

    for zoom in range(zoom_min, zoom_max + 1):
        x_min, y_max = deg2num(lat_min, lon_min, zoom)
        x_max, y_min = deg2num(lat_max, lon_max, zoom)

        # Swap if needed
        if x_min > x_max: x_min, x_max = x_max, x_min
        if y_min > y_max: y_min, y_max = y_max, y_min

        print(f"Zoom {zoom} indiriliyor: X[{x_min}-{x_max}], Y[{y_min}-{y_max}]")
        
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                tile_dir = os.path.join(output_dir, str(zoom), str(x))
                if not os.path.exists(tile_dir):
                    os.makedirs(tile_dir)
                
                tile_path = os.path.join(tile_dir, f"{y}.png")
                
                if not os.path.exists(tile_path):
                    url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
                    try:
                        resp = requests.get(url, headers=headers, timeout=5)
                        if resp.status_code == 200:
                            with open(tile_path, 'wb') as f:
                                f.write(resp.content)
                            downloaded_tiles += 1
                            time.sleep(0.05) # Sunucuya yüklenmemek için bekleme
                        else:
                            print(f"Hata {resp.status_code}: {url}")
                    except Exception as e:
                        print(f"İstisna oluştu {url}: {e}")
                
                total_tiles += 1
                if total_tiles % 100 == 0:
                    print(f"İşlenen tile sayısı: {total_tiles} (İndirilen: {downloaded_tiles})")

    print("İndirme tamamlandı!")

if __name__ == "__main__":
    # Istanbul Merkezi (Test için optimize edilmiş alan)
    # Zoom 10-13 (Makul boyut)
    # Lat: 40.95 - 41.10
    # Lon: 28.90 - 29.10
    
    output_path = os.path.join("istanbul_ulasim", "static", "tiles")
    
    # 1. Geniş Çerçeve (Zoom 10-12)
    print("Geniş çerçeve indiriliyor (Zoom 10-12)...")
    download_tiles(10, 12, 40.80, 41.30, 28.60, 29.50, output_path)
    
    # 2. Şehir Merkezi Detaylı (Zoom 13-14)
    print("Şehir merkezi detaylı indiriliyor (Zoom 13-14)...")
    download_tiles(13, 14, 40.95, 41.10, 28.90, 29.10, output_path)
