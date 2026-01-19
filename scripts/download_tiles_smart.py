
import os
import math
import requests
import time
import random
import threading

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------

# İstanbul Bounding Box (Uygulamadaki max_bounds ile uyumlu)
MIN_LAT = 40.80
MAX_LAT = 41.40
MIN_LON = 27.90
MAX_LON = 30.00

# Zoom Levels to Download
# 10-13: Genel harita görünümü (Tüm il sınırlarını kapsar)
# 14-15: Detaylı görünüm (İsteğe bağlı, çok yer kaplar)
ZOOM_LEVELS = [10, 11, 12, 13]

# Output Directory
OUTPUT_DIR = r"c:\Users\PC\Desktop\PROJECT-YTU\istanbul_ulasim\static\tiles"

# Tile Server (OpenStreetMap)
TILE_SERVER = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
HEADERS = {
    "User-Agent": "YTU_Transport_Project/1.0 (Student Research Project)"
}

# -------------------------------------------------------------------
# FUNCTIONS
# -------------------------------------------------------------------

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def download_tile(z, x, y):
    url = TILE_SERVER.format(z=z, x=x, y=y)
    path = os.path.join(OUTPUT_DIR, str(z), str(x), f"{y}.png")

    if os.path.exists(path):
        return  # Already exists

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            # Be polite to the server
            time.sleep(random.uniform(0.05, 0.2))
        else:
            print(f"Failed: {url} ({response.status_code})")
    except Exception as e:
        print(f"Error downloading {z}/{x}/{y}: {e}")

def main():
    print(f"Starting download for Zoom Levels: {ZOOM_LEVELS}")
    print(f"BBox: Lat({MIN_LAT}-{MAX_LAT}), Lon({MIN_LON}-{MAX_LON})")
    
    total_tiles = 0
    
    for z in ZOOM_LEVELS:
        min_x, min_y = deg2num(MAX_LAT, MIN_LON, z)
        max_x, max_y = deg2num(MIN_LAT, MAX_LON, z)
        
        count = (max_x - min_x + 1) * (max_y - min_y + 1)
        total_tiles += count
        print(f"Zoom {z}: ~{count} tiles to check/download.")

    print(f"Total estimated tiles: {total_tiles}")
    print("Downloading... (This might take a while)")

    for z in ZOOM_LEVELS:
        min_x, min_y = deg2num(MAX_LAT, MIN_LON, z)
        max_x, max_y = deg2num(MIN_LAT, MAX_LON, z)

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                download_tile(z, x, y)
                # Basit bir ilerleme göstergesi
                if x % 10 == 0 and y % 10 == 0:
                    print(f"Processing Z{z} X{x} Y{y}...", end="\r")

    print("\nDownload process completed!")

if __name__ == "__main__":
    main()
