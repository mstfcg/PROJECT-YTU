import os
import requests
import time
import random
import math

# Tiles URL pattern (OpenStreetMap)
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OUTPUT_DIR = "istanbul_ulasim/static/tiles"

# Istanbul Boundaries for Offline Usage
# Covers: Avcilar to Maltepe, Sariyer to Coast
BOUNDS = {
    "north": 41.15,
    "south": 40.93,
    "west": 28.80,
    "east": 29.15
}

# Only downloading these levels to keep size manageable
ZOOM_LEVELS = [11, 12, 13]

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
        # Optional: Check file size to ensure it's not a corrupt 0-byte file
        if os.path.getsize(path) > 100:
            print(f"Skipping {z}/{x}/{y} (exists)")
            return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    try:
        # print(f"Downloading {url}...")
        response = requests.get(url, headers=HEADERS, timeout=5)
        
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            # Sleep slightly to avoid rate limiting
            time.sleep(0.05)
        else:
            print(f"Failed: {z}/{x}/{y} -> {response.status_code}")
    except Exception as e:
        print(f"Error {z}/{x}/{y}: {e}")

if __name__ == "__main__":
    print("Calculating tiles to download...")
    total_files = 0
    tasks = []

    for z in ZOOM_LEVELS:
        top_left = deg2num(BOUNDS["north"], BOUNDS["west"], z)
        bottom_right = deg2num(BOUNDS["south"], BOUNDS["east"], z)
        
        # Ranges are inclusive for the loop
        x_start, x_end = top_left[0], bottom_right[0]
        y_start, y_end = top_left[1], bottom_right[1]

        print(f"Zoom {z}: X[{x_start}-{x_end}], Y[{y_start}-{y_end}]")
        
        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                tasks.append((z, x, y))

    print(f"Total tiles to download: {len(tasks)}")
    print("Starting download... (This might take a minute)")
    
    for i, (z, x, y) in enumerate(tasks):
        download_tile(z, x, y)
        if i % 10 == 0:
            print(f"Progress: {i}/{len(tasks)}")

    print("Download complete.")
