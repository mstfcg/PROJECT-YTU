import math

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

# Central Istanbul Bounding Box (Roughly Ataturk Airport to Kadikoy/Uskudar)
# North: 41.08 (Levent/Maslak)
# South: 40.98 (Kadikoy/Zeytinburnu Sahil)
# West: 28.90 (Zeytinburnu/Bayrampasa)
# East: 29.05 (Uskudar/Kadikoy)

bounds = {
    "north": 41.08,
    "south": 40.98,
    "west": 28.90,
    "east": 29.05
}

zooms = [11, 12, 13]

for z in zooms:
    top_left = deg2num(bounds["north"], bounds["west"], z)
    bottom_right = deg2num(bounds["south"], bounds["east"], z)
    
    print(f"Zoom {z}:")
    print(f"  X range: {top_left[0]} to {bottom_right[0]}")
    print(f"  Y range: {top_left[1]} to {bottom_right[1]}")
    count = (bottom_right[0] - top_left[0] + 1) * (bottom_right[1] - top_left[1] + 1)
    print(f"  Total tiles: {count}")
    print("-" * 20)
