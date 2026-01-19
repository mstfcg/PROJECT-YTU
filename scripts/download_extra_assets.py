import os
import requests

ASSETS = [
    ("https://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap-glyphicons.css", "istanbul_ulasim/static/vendor/bootstrap/bootstrap-glyphicons.css"),
    ("https://cdn.jsdelivr.net/gh/python-visualization/folium/folium/templates/leaflet.awesome.rotate.min.css", "istanbul_ulasim/static/vendor/awesome-markers/leaflet.awesome.rotate.min.css")
]

def download_file(url, path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"Downloading {url} to {path}...")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            print("Success.")
        else:
            print(f"Failed: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    for url, path in ASSETS:
        download_file(url, path)
