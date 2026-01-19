import osmnx as ox

places = [
    "Kartal, Istanbul, Turkey",
    "Kartal, Turkey",
    "Kartal",
    "Kartal District"
]

for p in places:
    print(f"Testing: {p}")
    try:
        gdf = ox.geocode_to_gdf(p)
        print(f"OK: {p} - {gdf.geometry[0].bounds}")
    except Exception as e:
        print(f"FAIL: {p} - {e}")
