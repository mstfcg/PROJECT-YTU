from flask import Flask, render_template, request, url_for, jsonify, make_response
import psycopg2
import json
import folium
from folium.plugins import Draw
from itertools import permutations, product
import os
import math
from branca.element import Element
import webbrowser
from threading import Timer
import time

app = Flask(__name__)
POI_OVERRIDE_PATH = os.path.normpath(
    os.path.join(app.root_path, "..", "data", "poi_district_overrides.json")
)


def load_poi_district_overrides():
    try:
        with open(POI_OVERRIDE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except Exception as exc:
        print(f"POI override read error: {exc}")
        return []

    if not isinstance(data, list):
        return []

    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        category = (item.get("category") or "").strip().lower()
        name_norm = (item.get("name_norm") or "").strip().lower()
        district_norm = (item.get("district_norm") or "").strip().lower()
        if not category or not name_norm or not district_norm:
            continue
        out.append({
            "category": category,
            "name_norm": name_norm,
            "district_norm": district_norm,
        })
    return out

# -------------------------
# OFFLINE MOD İÇİN SABİT İLÇE KOORDİNATLARI (YEDEK)
# -------------------------
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

# -------------------------
# POI KATEGORİ STİLLERİ (Global)
# -------------------------
CAT_STYLES = {
    "hastane":    {"color": "red",         "icon": "hospital",       "prefix": "fa", "css": "red"},
    "okul":       {"color": "green",       "icon": "graduation-cap", "prefix": "fa", "css": "green"},
    "universite": {"color": "darkgreen",   "icon": "university",     "prefix": "fa", "css": "darkgreen"},
    "metro":      {"color": "blue",        "icon": "subway",         "prefix": "fa", "css": "blue"},
    "havalimani": {"color": "darkblue",    "icon": "plane",          "prefix": "fas", "css": "darkblue"},
    "metrobus":   {"color": "#dc2626",     "icon": "bus",            "prefix": "fa", "css": "#dc2626"},
    "marmaray":   {"color": "#0d9488",     "icon": "train",          "prefix": "fa", "css": "#0d9488"},
    "vapur":      {"color": "#38bdf8",     "icon": "ship",           "prefix": "fa", "css": "#38bdf8"},
    "otobus":     {"color": "purple",      "icon": "bus",            "prefix": "fa", "css": "purple"},
    "market":     {"color": "lightred",    "icon": "shopping-cart",  "prefix": "fa", "css": "#ff6666"},
    "park":       {"color": "lightgreen",  "icon": "tree",           "prefix": "fa", "css": "lightgreen"},
    "plaj":       {"color": "beige",       "icon": "umbrella-beach", "prefix": "fa", "css": "#f5f5dc"},
    "avm":        {"color": "pink",        "icon": "shopping-bag",   "prefix": "fa", "css": "pink"},
    "eczane":     {"color": "darkred",     "icon": "notes-medical",  "prefix": "fa", "css": "darkred"},
    "otel":       {"color": "darkpurple",  "icon": "bed",            "prefix": "fa", "css": "#7c3aed"},
}

# -------------------------
# Ortalama hız profilleri (km/h)
# -------------------------
SPEED_WALK_KMH = 4.8
SPEED_CAR_KMH = {
    "normal": 40.0,
    "trafik": 20.0,
    "gece": 50.0,
}

ADDRESS_SEARCH_RADIUS_M = 600
ADDRESS_EXACT_MAX_M = 80
ADDRESS_NEAR_MAX_M = 400

def get_avg_speed_kmh(mode="araba", speed_profile="normal"):
    if mode == "yaya":
        return SPEED_WALK_KMH
    profile = (speed_profile or "normal").strip().lower()
    return SPEED_CAR_KMH.get(profile, SPEED_CAR_KMH["normal"])


def _format_address_text(row):
    if not row:
        return None
    name, house_number, street, neighbourhood, district, city, postcode, full_address = row
    if full_address:
        return full_address

    parts = []
    if name:
        parts.append(name)
    if street and house_number:
        parts.append(f"{street} {house_number}")
    elif street:
        parts.append(street)
    elif house_number:
        parts.append(house_number)
    if neighbourhood:
        parts.append(neighbourhood)
    if district:
        parts.append(district)
    if city:
        parts.append(city)
    if postcode:
        parts.append(postcode)
    return ", ".join([p for p in parts if p]) if parts else None

def normalize_tr_text(text):
    if text is None:
        return ""
    replacements = {
        "ı": "i",
        "İ": "i",
        "I": "i",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ş": "s",
        "Ş": "s",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    }
    out = text
    for tr_char, en_char in replacements.items():
        out = out.replace(tr_char, en_char)
    return out.lower().strip()

TR_TRANSLATE_SRC = "ığüşöç"
TR_TRANSLATE_DST = "igusoc"


def normalize_tr_basic(text):
    if text is None:
        return ""
    return text.lower().translate(str.maketrans(TR_TRANSLATE_SRC, TR_TRANSLATE_DST)).strip()

MARMARAY_ORDER = [
    "Gebze",
    "Darıca",
    "Osmangazi",
    "Fatih",
    "Çayırova",
    "Tuzla",
    "İçmeler",
    "Aydıntepe",
    "Güzelyalı",
    "Tersane",
    "Kaynarca",
    "Pendik",
    "Yunus",
    "Kartal",
    "Başak",
    "Atalar",
    "Cevizli",
    "Maltepe",
    "Süreyya Plajı",
    "İdealtepe",
    "Küçükyalı",
    "Bostancı",
    "Suadiye",
    "Erenköy",
    "Göztepe",
    "Feneryolu",
    "Söğütlüçeşme",
    "Ayrılık Çeşmesi",
    "Üsküdar",
    "Sirkeci",
    "Yenikapı",
    "Kazlıçeşme",
    "Zeytinburnu",
    "Yenimahalle",
    "Bakırköy",
    "Ataköy",
    "Yeşilyurt",
    "Yeşilköy",
    "Florya Akvaryum",
    "Florya",
    "Küçükçekmece",
    "Mustafa Kemal",
    "Halkalı",
]
MARMARAY_ORDER_INDEX = {
    normalize_tr_basic(name): idx for idx, name in enumerate(MARMARAY_ORDER)
}

def get_marmaray_order_index(name):
    key = normalize_tr_basic(name)
    return MARMARAY_ORDER_INDEX.get(key)

METROBUS_ORDER = [
    "Söğütlüçeşme",
    "Fikirtepe",
    "Uzunçayır",
    "Acıbadem",
    "Altunizade",
    "Burhaniye",
    "15 Temmuz Şehitler Köprüsü",
    "Mecidiyeköy",
    "Çağlayan",
    "Okmeydanı",
    "Okmeydanı Hastane",
    "Darülaceze - Perpa",
    "Halıcıoğlu",
    "Ayvansaray - Eyüp Sultan",
    "Edirnekapı",
    "Bayrampaşa - Maltepe",
    "Topkapı - Şehit Mustafa Cambaz",
    "Cevizlibağ",
    "Merter",
    "Zeytinburnu",
    "İncirli",
    "Bahçelievler",
    "Şirinevler",
    "Yenibosna",
    "Sefaköy",
    "Beşyol",
    "Florya",
    "Cennet Mahallesi",
    "Küçükçekmece",
    "Şükrübey",
    "Cihangir - Üniversite Mahallesi",
    "Avcılar Merkez",
    "Güzelyurt",
    "Haramidere",
    "Haramidere Sanayi",
    "Saadetdere Mahallesi",
    "Beykent",
    "Beylikdüzü Belediye",
    "Beylikdüzü",
    "Beylikdüzü Sondurak",
]
METROBUS_ORDER_INDEX = {
    normalize_tr_basic(name): idx for idx, name in enumerate(METROBUS_ORDER)
}

def get_metrobus_order_index(name):
    key = normalize_tr_basic(name)
    return METROBUS_ORDER_INDEX.get(key)

def resolve_district_from_name_filter(districts, district, name_filter):
    normalized_name_filter = normalize_tr_basic(name_filter)
    if not district and normalized_name_filter:
        for d in districts:
            if normalize_tr_basic(d) == normalized_name_filter:
                district = d
                name_filter = ""
                normalized_name_filter = ""
                break
    if district and normalized_name_filter and normalize_tr_basic(district) == normalized_name_filter:
        name_filter = ""
        normalized_name_filter = ""
    return district, name_filter, normalized_name_filter


def resolve_district_boundary(cur, district):
    has_boundary = False
    boundary_name = district
    
    if district:
        # Sadece admin_level='6' (İlçe) olanları kabul et.
        # Diğerleri bina, park vs. olabileceği için harita gösteriminde yanıltıcı oluyor.
        # Bulunamayanlar için statik GeoJSON dosyaları devreye girecek.
        cur.execute(
            "SELECT name FROM osm_istanbul_multipolygons WHERE name ILIKE %s AND admin_level='6' LIMIT 1",
            (district,),
        )
        row = cur.fetchone()
        if row:
            has_boundary = True
            boundary_name = row[0]

    return has_boundary, boundary_name


def get_district_geojson(conn, district_name):
    """
    İlçe sınırlarını önce veritabanından, bulamazsa statik JSON dosyasından getirir.
    Veritabanı verisi çok küçükse (hatalıysa) statik dosyayı tercih eder.
    """
    if not district_name:
        return None

    db_geojson = None
    db_area = 0

    # 1. Veritabanından dene
    try:
        with conn.cursor() as cur:
            has_boundary, boundary_name = resolve_district_boundary(cur, district_name)
            if has_boundary:
                cur.execute(
                    "SELECT ST_AsGeoJSON(wkb_geometry), ST_Area(wkb_geometry) "
                    "FROM osm_istanbul_multipolygons "
                    "WHERE name ILIKE %s LIMIT 1",
                    (boundary_name,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    db_geojson = json.loads(row[0])
                    db_area = row[1] if row[1] else 0
    except Exception as e:
        print(f"DB GeoJSON error: {e}")

    # 2. Statik dosyalardan dene (Fallback veya Better Match)
    try:
        # Örn: "Kartal" -> "kartal"
        safe_name = normalize_tr_basic(district_name).lower().replace(" ", "")
        geojson_path = os.path.join(app.root_path, "static", "geojson", f"{safe_name}.json")
        
        # Eğer veritabanı verisi yoksa veya alanı çok küçükse (< 0.001 derece kare ~ 10km2)
        # ve statik dosyamız varsa, statik dosyayı kullan.
        # Adalar için veritabanı 0.000146 dönüyor, bu yüzden statik dosyaya düşecek.
        # Bazı ilçeler için veritabanı verisi yerine özel çizimlerimizi zorunlu kılıyoruz.
        FORCE_FILE_DISTRICTS = ["uskudar", "adalar", "kartal", "pendik", "tuzla", "arnavutkoy", "catalca", "silivri", "beykoz", "sile", "beylikduzu", "buyukcekmece", "kucukcekmece", "cekmekoy", "eyupsultan", "beyoglu"]

        if os.path.exists(geojson_path):
            if not db_geojson or db_area < 0.001 or safe_name in FORCE_FILE_DISTRICTS:
                with open(geojson_path, "r", encoding="utf-8") as f:
                    return json.load(f)
    except Exception as e:
        print(f"File GeoJSON error: {e}")

    return db_geojson


def apply_pois_filters(
    query,
    params,
    selected_categories,
    district,
    name_filter,
    normalized_name_filter,
    has_boundary,
    boundary_name,
    custom_geojson_geometry=None,
    district_overrides=None,
    use_district_label=False,
):
    if selected_categories:
        placeholders = ",".join(["%s"] * len(selected_categories))
        query += f" AND category IN ({placeholders})"
        params.extend(selected_categories)

    if district:
        district_conditions = []
        district_params = []
        if use_district_label:
            normalized_district = normalize_tr_basic(district)
            district_conditions.append(
                " (district ILIKE %s OR "
                f"translate(lower(district), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') ILIKE %s)"
            )
            district_params.extend([f"%{district}%", f"%{normalized_district}%"])
        else:
            if custom_geojson_geometry:
                district_conditions.append(
                    " ST_Within(pois.geom, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))"
                )
                district_params.append(json.dumps(custom_geojson_geometry))
            elif has_boundary:
                district_conditions.append(
                    " ST_Within("
                    " pois.geom, "
                    " (SELECT wkb_geometry FROM osm_istanbul_multipolygons WHERE name ILIKE %s LIMIT 1)"
                    " )"
                )
                district_params.append(boundary_name)
            else:
                normalized_district = normalize_tr_basic(district)
                district_conditions.append(
                    " (district ILIKE %s OR "
                    f"translate(lower(district), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') ILIKE %s)"
                )
                district_params.extend([f"%{district}%", f"%{normalized_district}%"])

        if district_overrides:
            for category, name_norm in district_overrides:
                district_conditions.append(
                    " (category = %s AND "
                    f"translate(lower(name), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') = %s)"
                )
                district_params.extend([category, name_norm])

        if district_conditions:
            query += " AND (" + " OR ".join(district_conditions) + ")"
            params.extend(district_params)

    if name_filter:
        query += (
            " AND (name ILIKE %s OR "
            f"translate(lower(name), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') ILIKE %s OR "
            "district ILIKE %s OR "
            f"translate(lower(district), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') ILIKE %s)"
        )
        params.extend([
            f"%{name_filter}%",
            f"%{normalized_name_filter}%",
            f"%{name_filter}%",
            f"%{normalized_name_filter}%",
        ])

    return query, params

def extract_geojson_latlon(geojson):
    if not geojson:
        return []
    gtype = geojson.get("type")
    if gtype == "FeatureCollection":
        out = []
        for feature in geojson.get("features", []):
            out.extend(extract_geojson_latlon(feature))
        return out
    if gtype == "Feature":
        return extract_geojson_latlon(geojson.get("geometry"))
    geom = geojson.get("geometry", geojson)
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not gtype or coords is None:
        return []
    out = []
    def add_point(pt):
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            out.append((pt[1], pt[0]))
    if gtype == "Point":
        add_point(coords)
    elif gtype == "MultiPoint":
        for pt in coords:
            add_point(pt)
    elif gtype == "LineString":
        for pt in coords:
            add_point(pt)
    elif gtype == "MultiLineString":
        for line in coords:
            for pt in line:
                add_point(pt)
    elif gtype == "Polygon":
        for ring in coords:
            for pt in ring:
                add_point(pt)
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                for pt in ring:
                    add_point(pt)
    elif gtype == "GeometryCollection":
        for sub in geom.get("geometries", []):
            out.extend(extract_geojson_latlon(sub))
    return out


def add_district_boundary(m, boundary_geojson):
    if not boundary_geojson:
        return []
    try:
        folium.GeoJson(
            boundary_geojson,
            name="İlçe Sınırı",
            style_function=lambda x: {
                "color": "#e11d48",  # Kırmızımsı daha belirgin renk
                "weight": 3,         # Kalınlık arttı
                "fillColor": "#e11d48",
                "fillOpacity": 0.1,  # Hafif dolgu
                "dashArray": "5, 5"  # Kesikli çizgi efekti
            },
            tooltip="Seçilen İlçe Sınırı"
        ).add_to(m)
    except Exception:
        return []
    return extract_geojson_latlon(boundary_geojson)

def normalize_poi_category(category):
    if not isinstance(category, str):
        return category
    cat = category.strip().lower()
    if cat == "havalimanı" or cat == "airport":
        return "havalimani"
    if cat == "metrobüs":
        return "metrobus"
    if cat == "üniversite":
        return "universite"
    if cat == "otobüs" or cat == "otobüs durağı":
        return "otobus"
    if cat == "vapur iskelesi":
        return "vapur"
    return cat

def build_poi_div_icon(category, styles=None):
    styles = styles or CAT_STYLES
    style = styles.get(category, {"color": "gray", "icon": "info", "prefix": "fa"})
    css_color = style.get("css", style.get("color", "gray"))
    icon_html = f"""
        <div style="
            background-color: {css_color};
            color: white;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 1px 4px rgba(0,0,0,0.4);
            border: 2px solid white;
        ">
            <i class="{style.get('prefix', 'fa')} fa-{style.get('icon', 'info')}"></i>
        </div>
    """
    return folium.DivIcon(
        icon_size=(28, 28),
        icon_anchor=(14, 14),
        html=icon_html
    )

def make_category_key(category):
    if category is None:
        return ""
    return normalize_tr_text(str(category)).replace(" ", "-")

def group_poi_results_by_category(poi_results):
    grouped = {}
    for item in poi_results:
        cat = item.get("category") if isinstance(item, dict) else None
        display_cat = cat if cat is not None else "diger"
        grouped.setdefault(display_cat, []).append(item)

    def _sort_key(item):
        order_index = item.get("order_index")
        if isinstance(order_index, int):
            return order_index
        distance = item.get("distance_m")
        if distance is None:
            return float("inf")
        return distance

    for items in grouped.values():
        items.sort(key=_sort_key)

    ordered_keys = sorted(
        grouped.keys(),
        key=lambda k: grouped[k][0].get("distance_m", float("inf")) if grouped[k] else float("inf"),
    )

    out = []
    for cat in ordered_keys:
        items = grouped[cat]
        out.append({
            "is_group": True,
            "category": cat,
            "key": make_category_key(cat),
            "count": len(items),
        })
        out.extend(items)
    return out

# -------------------------
# OFFLINE HARİTA YARDIMCISI
# -------------------------
_TILE_BOUNDS_CACHE = None


def _tile_xyz_to_latlon_bounds(zoom, min_x, max_x, min_y, max_y):
    def tile2lon(x, z):
        return x / (2 ** z) * 360.0 - 180.0

    def tile2lat(y, z):
        n = math.pi - 2.0 * math.pi * y / (2 ** z)
        return math.degrees(math.atan(math.sinh(n)))

    west = tile2lon(min_x, zoom)
    east = tile2lon(max_x + 1, zoom)
    north = tile2lat(min_y, zoom)
    south = tile2lat(max_y + 1, zoom)
    return [[south, west], [north, east]]


def get_offline_tile_bounds():
    global _TILE_BOUNDS_CACHE
    if _TILE_BOUNDS_CACHE is not None:
        return _TILE_BOUNDS_CACHE

    tiles_root = os.path.join(app.root_path, "static", "tiles")
    if not os.path.isdir(tiles_root):
        return None

    zoom_dirs = [
        d for d in os.listdir(tiles_root)
        if d.isdigit() and os.path.isdir(os.path.join(tiles_root, d))
    ]
    zoom_dirs.sort(key=int)
    for z in zoom_dirs:
        zdir = os.path.join(tiles_root, z)
        min_x = min_y = None
        max_x = max_y = None
        for x_name in os.listdir(zdir):
            x_path = os.path.join(zdir, x_name)
            if not os.path.isdir(x_path):
                continue
            try:
                x = int(x_name)
            except ValueError:
                continue
            for y_name in os.listdir(x_path):
                if not y_name.endswith(".png"):
                    continue
                try:
                    y = int(os.path.splitext(y_name)[0])
                except ValueError:
                    continue
                if min_x is None:
                    min_x = max_x = x
                    min_y = max_y = y
                else:
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)
        if min_x is not None:
            _TILE_BOUNDS_CACHE = _tile_xyz_to_latlon_bounds(int(z), min_x, max_x, min_y, max_y)
            return _TILE_BOUNDS_CACHE
    return None


def create_offline_map(location, zoom_start=12, conn=None, max_bounds_override=None):
    # Harita sınırları (max_bounds) - İndirilen tile alanına göre (Genişletilmiş)
    # North: 41.30, South: 40.80, West: 28.50, East: 29.45
    bounds = max_bounds_override or get_offline_tile_bounds() or [[40.80, 28.50], [41.30, 29.45]]
    south, west = bounds[0]
    north, east = bounds[1]

    # tiles=None ile başla, sonra yerel TileLayer ekle
    m = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles=None,
        min_zoom=10,
        max_zoom=18,
        max_bounds=bounds,
        min_lat=south,
        max_lat=north,
        min_lon=west,
        max_lon=east
    )
    try:
        m.options["maxBoundsViscosity"] = 1.0
    except Exception:
        pass
    
    # Yerel Tile Layer
    folium.TileLayer(
        tiles="/static/tiles/{z}/{x}/{y}.png",
        attr="Offline Map (YTU Project)",
        min_zoom=10,
        max_zoom=18,
        max_native_zoom=16, # Tile'lar 16'ya kadar var, sonrası scale edilsin
        tms=False,
        no_wrap=True
    ).add_to(m)

    return m

def inject_offline_assets(map_html_path):
    """
    Oluşturulan HTML harita dosyasını okur,
    içindeki CDN linklerini yerel (static/vendor) linklerle değiştirir
    ve dosyayı günceller.
    """
    try:
        with open(map_html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Leaflet CSS
        content = content.replace(
            'https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css',
            '/static/vendor/leaflet/leaflet.css'
        )
        # 2. Leaflet JS
        content = content.replace(
            'https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js',
            '/static/vendor/leaflet/leaflet.js'
        )
        # 3. Bootstrap CSS
        content = content.replace(
            'https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css',
            '/static/vendor/bootstrap/bootstrap.min.css'
        )
        # 4. Bootstrap JS
        content = content.replace(
            'https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/js/bootstrap.bundle.min.js',
            '/static/vendor/bootstrap/bootstrap.bundle.min.js'
        )
        # 5. JQuery
        content = content.replace(
            'https://code.jquery.com/jquery-3.7.1.min.js',
            '/static/vendor/jquery/jquery-3.7.1.min.js'
        )
        # 6. FontAwesome
        content = content.replace(
            'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.2.0/css/all.min.css',
            '/static/vendor/fontawesome/all.min.css'
        )
        # 7. Awesome Markers JS
        content = content.replace(
            'https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.js',
            '/static/vendor/awesome-markers/leaflet.awesome-markers.js'
        )
        # 8. Awesome Markers CSS
        content = content.replace(
            'https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.css',
            '/static/vendor/awesome-markers/leaflet.awesome-markers.css'
        )

        # 9. Extra CSS
        content = content.replace(
            'https://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap-glyphicons.css',
            '/static/vendor/bootstrap/bootstrap-glyphicons.css'
        )
        content = content.replace(
            'https://cdn.jsdelivr.net/gh/python-visualization/folium/folium/templates/leaflet.awesome.rotate.min.css',
            '/static/vendor/awesome-markers/leaflet.awesome.rotate.min.css'
        )

        # 10. Arka plan rengi (Tiles olmadığı için gri/siyah zemin)
        # Leaflet container'ına stil ekleyelim - Karasal bütünlük için açık bej/toprak rengi (#f2efe9)
        content = content.replace(
            '.leaflet-container { font-size: 1rem; }',
            '.leaflet-container { font-size: 1rem; background-color: #f2efe9; }'
        )

        with open(map_html_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    except Exception as e:
        print(f"Offline asset injection hatası: {e}")

def save_map_html(m, template_name, endpoint=None, **url_kwargs):
    map_path = os.path.join(app.root_path, "templates", template_name)
    m.save(map_path)
    inject_offline_assets(map_path)
    if endpoint:
        return url_for(endpoint, **url_kwargs)
    return None

def close_conn(conn):
    try:
        if conn:
            conn.close()
    except Exception:
        pass

def format_db_error(err):
    return f"Veritabanina baglanirken hata olustu: {err}"

# -------------------------
# Veritabanı bağlantı bilgileri
# -------------------------
DB_NAME = os.getenv("DB_NAME", "istanbul_gis")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456Qq")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")


def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    return conn


def init_db_connection():
    try:
        conn = get_db_connection()
    except Exception as e:
        return None, False, "", format_db_error(e)

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
    except Exception as e:
        close_conn(conn)
        return None, False, "", format_db_error(e)

    db_message = f"Veritabani baglantisi basarili. PostgreSQL versiyonu: {version}"
    return conn, True, db_message, None


# -------------------------
# Geocoding: Semt / adres → (lat, lon)
# -------------------------

@app.route("/reverse_geocode")
def reverse_geocode_api():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    mode = request.args.get("mode", "araba").strip().lower()
    if mode not in ("araba", "yaya"):
        mode = "araba"

    if lat is None or lon is None:
        return jsonify({"address": None, "error": "lat/lon eksik"}), 400

    # Offline modda veritabanından en yakın POI'yi bulmaya çalışalım
    try:
        conn = get_db_connection()
        address_found = None
        snapped_lat = lat
        snapped_lon = lon
        node_id = None
        
        with conn.cursor() as cur:
            try:
                snapped_lat, snapped_lon = snap_point_to_road(conn, lat, lon, mode=mode)
                node_id = find_nearest_node(conn, snapped_lat, snapped_lon, mode=mode)
            except Exception as e_snap:
                print(f"Snap error: {e_snap}")
                conn.rollback()
            # 1. Adım: Adres tablosundan ara (Öncelikli)
            try:
                sql_addr = """
                    SELECT
                        name,
                        house_number,
                        street,
                        neighbourhood,
                        district,
                        city,
                        postcode,
                        full_address,
                        ST_Distance(
                            geom::geography,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                        ) as dist
                    FROM osm_addresses
                    WHERE ST_DWithin(
                        geom::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s
                    )
                    ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    LIMIT 1;
                """
                cur.execute(
                    sql_addr,
                    (lon, lat, lon, lat, ADDRESS_SEARCH_RADIUS_M, lon, lat),
                )
                row_addr = cur.fetchone()
                if row_addr:
                    addr_text = _format_address_text(row_addr[:8])
                    dist = row_addr[8]
                    if addr_text and dist is not None:
                        if dist <= ADDRESS_EXACT_MAX_M:
                            address_found = addr_text
                        elif dist <= ADDRESS_NEAR_MAX_M:
                            address_found = f"{addr_text} yakınlarında ({int(dist)}m)"
            except Exception as e_addr:
                print(f"OSM address search error: {e_addr}")
                conn.rollback()

            # 2. Adım: POIS tablosundan ara (Yedek)
            sql_pois = """
                SELECT name, category,
                       ST_Distance(
                           geom::geography,
                           ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                       ) as dist
                FROM pois
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                LIMIT 1;
            """
            if not address_found:
                cur.execute(sql_pois, (lon, lat, lon, lat))
                row = cur.fetchone()
                
                if row:
                    name, category, dist = row
                    if dist < 100:
                        address_found = name
                    elif dist < 1000:
                        address_found = f"{name} yakınlarında ({int(dist)}m)"

            # 3. Adım: Eğer POIS'ten anlamlı bir şey çıkmadıysa osm_istanbul_points tablosuna bak
            if not address_found:
                try:
                    sql_osm = """
                        SELECT name, place,
                               ST_Distance(
                                   geom::geography,
                                   ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                               ) as dist
                        FROM osm_istanbul_points
                        WHERE name IS NOT NULL
                        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                        LIMIT 1;
                    """
                    cur.execute(sql_osm, (lon, lat, lon, lat))
                    row_osm = cur.fetchone()
                    if row_osm:
                        osm_name, osm_place, osm_dist = row_osm
                        if osm_dist < 200:
                            address_found = osm_name
                        elif osm_dist < 1000:
                            address_found = f"{osm_name} yakınlarında ({int(osm_dist)}m)"
                except Exception as e_osm:
                    print(f"OSM Points search error: {e_osm}")
                    conn.rollback()

        close_conn(conn)
        
        if not address_found:
            address_found = f"Konum: {lat:.5f}, {lon:.5f}"
        
        # Eğer POI bulunamazsa koordinatları dön
        return jsonify({
            "address": address_found,
            "snapped_lat": snapped_lat,
            "snapped_lon": snapped_lon,
            "node_id": node_id
        })
        
    except Exception as e:
        print(f"Offline reverse geocode hatası: {e}")
        # Hata durumunda da en azından koordinatı gösterelim
        return jsonify({
            "address": f"Konum: {lat:.5f}, {lon:.5f}",
            "snapped_lat": lat,
            "snapped_lon": lon,
            "node_id": None
        })

def _parse_lat_lon_input(place_name):
    if "," not in place_name:
        return None
    try:
        parts = place_name.split(",")
        if len(parts) != 2:
            return None
        lat_val = float(parts[0].strip())
        lon_val = float(parts[1].strip())
        return lat_val, lon_val
    except ValueError:
        return None


def _query_pois_coords(cur, name):
    # Türkçe karakter dönüşümü için SQL tarafında translate kullanımı
    # name parametresi zaten Python tarafında normalize edilmeden gelebilir.
    # Hem saf name ile hem de normalize edilmiş haliyle arayalım.
    
    # 1. name ILIKE %s
    # 2. translate(lower(name), ...) ILIKE %s
    
    normalized_input = normalize_tr_basic(name)
    
    query_sql = f"""
        SELECT ST_Y(geom::geometry), ST_X(geom::geometry)
        FROM pois
        WHERE 
            name ILIKE %s OR
            translate(lower(name), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') ILIKE %s
        ORDER BY
          CASE
            WHEN name ILIKE %s THEN 0
            WHEN translate(lower(name), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') ILIKE %s THEN 1
            WHEN name ILIKE %s THEN 2
            ELSE 3
          END ASC,
          length(name) ASC
        LIMIT 1
    """
    
    p_full = name
    p_norm_full = normalized_input
    
    p_starts = f"{name}%"
    p_norm_starts = f"{normalized_input}%"
    
    p_contains = f"%{name}%"
    p_norm_contains = f"%{normalized_input}%"
    
    # Parametre sırası: 
    # WHERE: p_contains, p_norm_contains
    # ORDER BY: p_full, p_norm_full, p_starts
    
    cur.execute(query_sql, (p_contains, p_norm_contains, p_full, p_norm_full, p_starts))
    row = cur.fetchone()
    if row:
        return row[0], row[1]
    return None


def _query_osm_point_coords(cur, name):
    normalized_input = normalize_tr_basic(name)
    query_osm = f"""
        SELECT ST_Y(geom::geometry), ST_X(geom::geometry)
        FROM osm_istanbul_points
        WHERE 
            name ILIKE %s OR
            translate(lower(name), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') ILIKE %s
        LIMIT 1
    """
    p_contains = f"%{name}%"
    p_norm_contains = f"%{normalized_input}%"
    
    cur.execute(query_osm, (p_contains, p_norm_contains))
    row_osm = cur.fetchone()
    if row_osm:
        return row_osm[0], row_osm[1]
    return None

def _query_pois_with_district(cur, name_part, district_part):
    """
    Hem isim hem ilçe eşleşmesi arar.
    name_part: "Esenkent" gibi (raw)
    district_part: "Maltepe" gibi (raw veya normalized)
    """
    norm_name = normalize_tr_basic(name_part)
    norm_dist = normalize_tr_basic(district_part)
    
    query = f"""
        SELECT ST_Y(geom::geometry), ST_X(geom::geometry)
        FROM pois
        WHERE 
            (name ILIKE %s OR translate(lower(name), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') ILIKE %s)
            AND
            (district ILIKE %s OR translate(lower(district), '{TR_TRANSLATE_SRC}', '{TR_TRANSLATE_DST}') ILIKE %s)
        LIMIT 1
    """
    p_name_like = f"%{name_part}%"
    p_name_norm_like = f"%{norm_name}%"
    p_dist_like = f"%{district_part}%"
    p_dist_norm_like = f"%{norm_dist}%"
    
    cur.execute(query, (p_name_like, p_name_norm_like, p_dist_like, p_dist_norm_like))
    row = cur.fetchone()
    if row:
        return row
    return None

_DISTRICT_SUFFIXES = {"ilce", "ilcesi", "istanbul", "belediyesi", "belediye"}


def _normalize_place_tokens(place_name):
    norm = normalize_tr_basic(place_name)
    norm = norm.replace(",", " ").replace(".", " ").replace("-", " ")
    norm = " ".join(norm.split())
    return norm.split()


def _resolve_district_coords(place_name):
    tokens = _normalize_place_tokens(place_name)
    if not tokens:
        return None
    candidate = None
    if len(tokens) == 1:
        candidate = tokens[0]
    elif len(tokens) == 2 and tokens[1] in _DISTRICT_SUFFIXES:
        candidate = tokens[0]
    elif len(tokens) == 3 and tokens[1] in ("ilce", "ilcesi") and tokens[2] == "istanbul":
        candidate = tokens[0]
    if candidate and candidate in KNOWN_DISTRICTS:
        return KNOWN_DISTRICTS[candidate]
    return None

def geocode_place(place_name: str):
    """
    Girilen semt/adres bilgisini kullanarak
    tamamen offline kaynaklardan (DB + yedek ilçe listesi) (lat, lon) döndürür.
    Tam adresler de desteklenir; farklı sorgu varyasyonları denenir.
    """
    if not place_name:
        return None
        
    place_name = place_name.strip()
    print(f"DEBUG: geocode_place called with '{place_name}'")

    try:
        # 1. Koordinat formati mi? "lat, lon"
        coords = _parse_lat_lon_input(place_name)
        if coords:
            lat_val, lon_val = coords
            print(f"DEBUG: Parsed coordinates: {lat_val}, {lon_val}")
            return coords

        district_coords = _resolve_district_coords(place_name)
        if district_coords:
            print(f"DEBUG: Matched district coords for '{place_name}': {district_coords}")
            return district_coords
        
        # 1.5. İlçe belirtilmiş mi? "Esenkent Maltepe" veya "Esenkent, Maltepe"
        detected_dist = None
        poi_part = None
        
        # Strategy A: Comma
        if "," in place_name:
            parts = place_name.split(",")
            cand = parts[-1].strip()
            if normalize_tr_basic(cand) in KNOWN_DISTRICTS:
                detected_dist = cand
                poi_part = ",".join(parts[:-1]).strip()
        
        # Strategy B: Space (last word) - sadece A bulunamadıysa
        if not detected_dist:
            parts = place_name.split()
            if len(parts) > 1:
                cand = parts[-1].strip()
                cand_norm = normalize_tr_basic(cand)
                # print(f"DEBUG: Checking candidate district: '{cand}' -> '{cand_norm}'")
                if cand_norm in KNOWN_DISTRICTS:
                    detected_dist = cand
                    poi_part = " ".join(parts[:-1]).strip()
                    # print(f"DEBUG: Strategy B matched! dist='{detected_dist}', poi='{poi_part}'")

        # 2. Veritabanında POIS tablosunda ara
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Eğer ilçe tespit edildiyse ÖNCE onu dene
                if detected_dist and poi_part:
                    print(f"DEBUG: District detected '{detected_dist}'. Searching POI '{poi_part}'...")
                    coords = _query_pois_with_district(cur, poi_part, detected_dist)
                    if coords:
                        print(f"DEBUG: Found in POIS table with district filter: {coords}")
                        return coords
                
                # Bulunamazsa (veya ilçe yoksa) normal arama
                coords = _query_pois_coords(cur, place_name)
                if coords:
                    print(f"DEBUG: Found in POIS table: {coords}")
                    return coords

                if "," in place_name:
                    first_part = place_name.split(",")[0].strip()
                    if first_part:
                        coords = _query_pois_coords(cur, first_part)
                        if coords:
                            print(f"DEBUG: Found in POIS table (first part): {coords}")
                            return coords

                print("DEBUG: Checking osm_istanbul_points table...")
                coords = _query_osm_point_coords(cur, place_name)
                if coords:
                    print(f"DEBUG: Found in OSM_ISTANBUL_POINTS: {coords}")
                    return coords

        finally:
            close_conn(conn)

    except Exception as e:
        print(f"DEBUG: DB search error: {e}")
    
    # 4. Veritabanında bulunamadıysa, sabit ilçe listesine bak (YEDEK)
    print(f"DEBUG: Checking KNOWN_DISTRICTS fallback...")
    try:
        temp_name = place_name
        replacements = {
            "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
            "İ": "i", "Ğ": "g", "Ü": "u", "Ş": "s", "Ö": "o", "Ç": "c",
            "I": "i" 
        }
        for tr, en in replacements.items():
            temp_name = temp_name.replace(tr, en)
        
        normalized_name = normalize_tr_basic(place_name)
        print(f"DEBUG: Normalized name: '{normalized_name}'")
            
        for dist_name, coords in KNOWN_DISTRICTS.items():
            if dist_name in normalized_name:
                print(f"DEBUG: Match found in KNOWN_DISTRICTS: {dist_name} -> {coords}")
                return coords
    except Exception as e:
            print(f"DEBUG: KNOWN_DISTRICTS fallback error: {e}")
    
    print(f"DEBUG: No match found anywhere.")
    return None


# -------------------------
# Yardımcı fonksiyon: Tablo seçimi (Whitelist)
# -------------------------
def get_routing_tables(mode):
    """
    Güvenli tablo seçimi (Whitelist).
    SQL Injection riskine karşı mode parametresini kontrol eder.
    Dönüş: (nodes_table, edges_table)
    """
    # Tablo isimleri veritabanındaki gerçek isimlerle (singular) eşleşmeli
    if mode == "yaya":
        # nodes_walk ve edges_walk tablolarını kullan
        return "nodes_walk", "edges_walk"
    
    # Varsayılan: araba
    return "nodes", "edges"

# -------------------------
# Yardımcı fonksiyon: en yakın node
# -------------------------
def find_nearest_node(conn, lat, lon, mode="araba"):
    """
    (lat, lon) noktasına en yakın node id'sini döndürür.
    nodes tablosu: id, geometry (Point, 4326)
    """
    nodes_table, edges_table = get_routing_tables(mode)
    
    # DEBUG LOG
    print(f"[DEBUG] find_nearest_node | mode={mode} | table={nodes_table} | lat={lat}, lon={lon}")

    with conn.cursor() as cur:
        # Eğer yaya modundaysak, 'id' sütunu bizim yeni integer ID'mizdir.
        # OSM ID ile karıştırmamak gerekir. pgRouting 'id'yi kullanacak.
        query = f"""
            SELECT id
            FROM {nodes_table}
            ORDER BY geometry <-> ST_SetSRID(ST_Point(%s, %s), 4326)
            LIMIT 1;
        """
        # ST_Point(longitude, latitude)
        cur.execute(query, (lon, lat))
        result = cur.fetchone()
        if result:
            return result[0]
        else:
            print(f"[DEBUG] find_nearest_node: Node bulunamadı.")
            return None


def find_candidate_nodes(conn, lat, lon, mode="araba", limit=5):
    nodes_table, edges_table = get_routing_tables(mode)
    
    # DEBUG LOG
    print(f"[DEBUG] find_candidate_nodes | mode={mode} | table={nodes_table} | limit={limit}")
    
    with conn.cursor() as cur:
        query = f"""
            SELECT id
            FROM {nodes_table}
            ORDER BY geometry <-> ST_SetSRID(ST_Point(%s, %s), 4326)
            LIMIT %s;
        """
        cur.execute(query, (lon, lat, limit))
        return [row[0] for row in cur.fetchall()]

def snap_point_to_road(conn, lat, lon, mode="araba"):
    nodes_table, edges_table = get_routing_tables(mode)
    
    with conn.cursor() as cur:
        query = f"""
            SELECT ST_AsText(
                ST_ClosestPoint(
                    e.geometry,
                    ST_SetSRID(ST_Point(%s, %s), 4326)
                )
            )
            FROM {edges_table} e
            ORDER BY e.geometry <-> ST_SetSRID(ST_Point(%s, %s), 4326)
            LIMIT 1;
        """
        cur.execute(query, (lon, lat, lon, lat))
        row = cur.fetchone()
        if row and row[0]:
            snapped = point_wkt_to_latlon(row[0])
            if snapped != (0, 0):
                return snapped
    return (lat, lon)


# -------------------------
# En kısa yol: pgr_dijkstra → geometri WKT'leri
# -------------------------
def get_route_geom_wkts(conn, start_node, end_node, mode="araba"):
    """
    pgr_dijkstra ile en kısa yolu hesaplar,
    edges tablosundan geometry sütunlarını WKT (LINESTRING) formatında döndürür.
    """
    nodes_table, edges_table = get_routing_tables(mode)
    
    # DEBUG LOG
    print(f"[DEBUG] get_route_geom_wkts | mode={mode} | table={edges_table} | start={start_node} -> end={end_node}")
    
    # directed = True for both because we populated reverse_cost in edges_walk
    # to be equal to cost, making it effectively bidirectional but traversable by standard Dijkstra.
    directed = True
    
    edges_sql = f"SELECT id, source, target, cost, reverse_cost FROM {edges_table}"
    with conn.cursor() as cur:
        query = f"""
            WITH route AS (
                SELECT * FROM pgr_dijkstra(
                    %s,
                    %s,
                    %s,
                    directed := %s
                )
            )
            SELECT 
                CASE 
                    WHEN r.node = e.source THEN ST_AsText(e.geometry)
                    ELSE ST_AsText(ST_Reverse(e.geometry))
                END AS wkt
            FROM route r
            JOIN {edges_table} e
              ON e.id = r.edge
            ORDER BY r.seq;
        """
        cur.execute(query, (edges_sql, start_node, end_node, directed))
        rows = cur.fetchall()
        return [r[0] for r in rows]


# -------------------------
# En kısa yol: pgr_dijkstra → sadece toplam mesafe
# -------------------------
def get_shortest_path_cost(conn, start_node, end_node, mode="araba"):
    """
    pgr_dijkstra ile start_node → end_node arasındaki
    toplam maliyeti (cost) döndürür.
    edges.cost = metre (OSM length)
    """
    nodes_table, edges_table = get_routing_tables(mode)
    
    # DEBUG LOG
    print(f"[DEBUG] get_shortest_path_cost | mode={mode} | table={edges_table} | start={start_node} -> end={end_node}")
    
    directed = True
    
    edges_sql = f"SELECT id, source, target, cost, reverse_cost FROM {edges_table}"
    with conn.cursor() as cur:
        query = """
            SELECT agg_cost
            FROM pgr_dijkstra(
                %s,
                %s,
                %s,
                directed := %s
            )
            ORDER BY seq DESC
            LIMIT 1;
        """
        cur.execute(query, (edges_sql, start_node, end_node, directed))
        row = cur.fetchone()
        if row and row[0] is not None:
            return float(row[0])
        return None


# -------------------------
# WKT LINESTRING -> (lat, lon) listesine çevir
# -------------------------
def linestring_wkt_to_latlon_list(wkt):
    """
    Örnek WKT: 'LINESTRING(28.9 41.0, 28.91 41.01, ...)'
    Bunu [(lat, lon), (lat, lon), ...] listesine çevirir.
    """
    if not wkt:
        return []
    wkt = wkt.replace("LINESTRING", "").replace("(", "").replace(")", "").strip()
    points = wkt.split(",")
    coords = []
    for p in points:
        p = p.strip()
        if not p:
            continue
        # Çoklu boşlukları desteklemek için split() parametresiz kullanılır
        parts = p.split()
        if len(parts) >= 2:
            try:
                lon = float(parts[0])
                lat = float(parts[1])
                coords.append((lat, lon))  # folium (lat, lon) bekliyor
            except ValueError:
                pass
    return coords


# -------------------------
# WKT POINT -> (lat, lon)
# -------------------------
def point_wkt_to_latlon(wkt):
    """
    Örnek WKT: 'POINT(28.9 41.0)' -> (lat, lon)
    """
    if not wkt:
        return (0, 0)
    wkt = wkt.replace("POINT", "").replace("(", "").replace(")", "").strip()
    parts = wkt.split()
    if len(parts) >= 2:
        try:
            lon = float(parts[0])
            lat = float(parts[1])
            return (lat, lon)
        except ValueError:
            return (0, 0)
    return (0, 0)

def bounds_from_coords(coords):
    if not coords:
        return None
    min_lat = min(c[0] for c in coords)
    min_lon = min(c[1] for c in coords)
    max_lat = max(c[0] for c in coords)
    max_lon = max(c[1] for c in coords)
    return [[min_lat, min_lon], [max_lat, max_lon]]

def merge_bounds(bounds_a, bounds_b):
    if bounds_a is None:
        return bounds_b
    if bounds_b is None:
        return bounds_a
    return [
        [min(bounds_a[0][0], bounds_b[0][0]), min(bounds_a[0][1], bounds_b[0][1])],
        [max(bounds_a[1][0], bounds_b[1][0]), max(bounds_a[1][1], bounds_b[1][1])],
    ]

def fit_bounds_from_coords(m, coords, bounds_limit=None):
    if not coords:
        return
    bounds = bounds_from_coords(coords)
    if not bounds:
        return
    min_lat, min_lon = bounds[0]
    max_lat, max_lon = bounds[1]
    limit = bounds_limit or get_offline_tile_bounds()
    if limit:
        south, west = limit[0]
        north, east = limit[1]
        min_lat = max(min_lat, south)
        min_lon = max(min_lon, west)
        max_lat = min(max_lat, north)
        max_lon = min(max_lon, east)
        if min_lat >= max_lat or min_lon >= max_lon:
            m.fit_bounds(limit)
            return
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])


def inject_map_click_js(m):
    """
    Folium haritasına tıklama ile üst (parent) sayfanın formunu dolduracak JS ekler.
    Parent → iframe'e seçim modu gönderebilir: start/end/via
    İframe → parent'a tıklanan koordinatı geri yollar.
    """
    click_js = """
    (function(){
      var selMode = 'start';
      window.addEventListener('message', function(e){
        var d = e.data || {};
        if (d.type === 'navSelMode') { selMode = d.value || 'start'; }
      });
      var attached = false;
      var tryAttach = function() {
        var name = Object.keys(window).find(function(k){ return /^map_/.test(k) && window[k] && typeof window[k].on === 'function'; });
        var mapObj = window[name];
        if (mapObj && !attached) {
          attached = true;
          mapObj.on('click', function(ev){
            var lat = ev.latlng.lat, lon = ev.latlng.lng;
            if (window.parent) {
              window.parent.postMessage({ type: 'navCoords', target: selMode, lat: lat, lon: lon }, '*');
            }
          });
        }
      };
      tryAttach();
      var iv = setInterval(function(){
        if (!attached) {
          tryAttach();
        } else {
          clearInterval(iv);
        }
      }, 250);
    })();
    """
    try:
        m.get_root().script.add_child(Element(click_js))
    except Exception:
        pass


def inject_map_draw_js(m):
    """
    Harita üzerindeki çizim olaylarını dinler ve parent pencereye iletir.
    """
    draw_js = """
    (function(){
      var attached = false;
      var tryAttach = function() {
        var name = Object.keys(window).find(function(k){ return /^map_/.test(k) && window[k] && typeof window[k].on === 'function'; });
        var mapObj = window[name];
        if (mapObj && !attached) {
          attached = true;
          // Leaflet Draw events
          mapObj.on(L.Draw.Event.CREATED, function (e) {
             var type = e.layerType,
                 layer = e.layer;
             // GeoJSON'a çevir
             var geojson = layer.toGeoJSON();
             if (window.parent) {
                 window.parent.postMessage({ type: 'drawCreated', geojson: JSON.stringify(geojson) }, '*');
             }
          });

          // Silme modu açıldığında sadece "Clear All" görünsün, Save/Cancel gizlensin
          mapObj.on('draw:deletestart', function() {
             setTimeout(function() {
                 var actions = document.querySelectorAll('.leaflet-draw-actions li a');
                 actions.forEach(function(a) {
                     var text = a.innerText.trim();
                     // Save ve Cancel butonlarını gizle
                     if (text === 'Save' || text === 'Cancel') {
                         a.parentElement.style.display = 'none';
                     }
                 });
             }, 10);
          });
        }
      };
      tryAttach();
      var iv = setInterval(function(){
        if (!attached) {
          tryAttach();
        } else {
          clearInterval(iv);
        }
      }, 250);
    })();
    """
    try:
        m.get_root().script.add_child(Element(draw_js))
    except Exception:
        pass



def inject_map_focus_js(m):
    """
    Harita iframe içinde çalışırken, dışarıdan (parent window) gelen 'focus_point' mesajını dinler.
    Gelen koordinata animasyonlu şekilde (flyTo) odaklanır.
    """
    focus_js = """
    (function(){
      var highlightLayer = null; // Vurgulama katmanını saklamak için
      var mapObj = null;

      function getMap() {
        var name = Object.keys(window).find(function(k){ return /^map_/.test(k) && window[k] && typeof window[k].flyTo === 'function'; });
        return window[name];
      }

      // 1. Dışarıdan gelen "focus" mesajlarını dinle (Listeye tıklama)
      window.addEventListener('message', function(e){
        var d = e.data || {};
        if (d.type === 'focus_point' && d.lat && d.lon) {
           mapObj = getMap();
           if (mapObj) {
             // 1. Oraya uç (Zoom yap)
             mapObj.flyTo([d.lat, d.lon], 18, {duration: 1.5});
             
             // 2. Varsa eski vurguyu kaldır
             if (highlightLayer) {
                 mapObj.removeLayer(highlightLayer);
             }

             // 3. Yeni vurgu ekle (Yanıp sönen daire efekti veya sabit belirgin daire)
             highlightLayer = L.circleMarker([d.lat, d.lon], {
                 radius: 20,           // Yarıçap (piksel)
                 color: '#FFD700',     // Çerçeve rengi (Altın sarısı)
                 weight: 3,            // Çerçeve kalınlığı
                 fillColor: '#FFD700', // Dolgu rengi
                 fillOpacity: 0.4      // Dolgu şeffaflığı
             }).addTo(mapObj);

             // 4. O konumdaki marker'ı bul ve Popup aç
             mapObj.eachLayer(function(layer) {
                if (layer.getLatLng && layer.openPopup) {
                    var ll = layer.getLatLng();
                    if (Math.abs(ll.lat - d.lat) < 0.0001 && Math.abs(ll.lng - d.lon) < 0.0001) {
                        layer.openPopup();
                    }
                }
             });
           }
        }
      });

      // 2. Haritadaki marker tıklamalarını (Popup açılmasını) dinle
      var iv = setInterval(function(){
          var m = getMap();
          if (m) {
              clearInterval(iv);
              mapObj = m;
              
              // Herhangi bir popup açıldığında oraya zoom yap
              mapObj.on('popupopen', function(e) {
                  var ll = e.popup.getLatLng();
                  if (ll) {
                      mapObj.flyTo(ll, 18, {duration: 1.5});
                      
                      // Varsa eski vurguyu kaldır
                      if (highlightLayer) {
                          mapObj.removeLayer(highlightLayer);
                      }

                      // Yeni vurgu ekle
                      highlightLayer = L.circleMarker(ll, {
                          radius: 20,
                          color: '#FFD700',
                          weight: 3,
                          fillColor: '#FFD700',
                          fillOpacity: 0.4
                      }).addTo(mapObj);
                  }
              });
          }
      }, 250);

    })();
    """
    try:
        m.get_root().script.add_child(Element(focus_js))
    except Exception:
        pass

def inject_map_toggle_draw_js(m):
    """
    Harita iframe içinde çalışırken, dışarıdan (parent window) gelen 'toggleDraw' mesajını dinler.
    Mod 'drawing' ise çizim araçlarını gösterir, 'radius' ise gizler.
    """
    toggle_js = """
    (function(){
      window.addEventListener('message', function(e){
        var d = e.data || {};
        if (d.type === 'toggleDraw' && d.mode) {
           var drawControl = document.querySelector('.leaflet-draw');
           if (drawControl) {
               if (d.mode === 'drawing') {
                   drawControl.style.display = 'block';
               } else {
                   drawControl.style.display = 'none';
               }
           }
        }
      });
    })();
    """
    try:
        m.get_root().script.add_child(Element(toggle_js))
    except Exception:
        pass

def compute_turn_steps(coords):
    """
    Basit adım-adım yönlendirme üretir:
    - Büyük açı değişimlerinde 'sağa dönün' / 'sola dönün'
    - Aralarda 'düz devam'
    Mesafeleri yaklaşık metre cinsinden verir.
    """
    import math
    def approx_distance_m(a, b):
        lat1, lon1 = a
        lat2, lon2 = b
        dx = (lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2.0))
        dy = (lat2 - lat1)
        return math.sqrt(dx*dx + dy*dy) * 111320.0
    def bearing(a, b):
        lat1, lon1 = a
        lat2, lon2 = b
        dlon = (lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2.0))
        dlat = (lat2 - lat1)
        ang = math.degrees(math.atan2(dlon, dlat))
        return ang
    steps = []
    if not coords or len(coords) < 2:
        return steps
    total_since_last = 0.0
    prev_bearing = bearing(coords[0], coords[1])
    prev_point = coords[1]
    for i in range(2, len(coords)):
        cur = coords[i]
        dist = approx_distance_m(prev_point, cur)
        total_since_last += dist
        b = bearing(prev_point, cur)
        delta = b - prev_bearing
        while delta > 180: delta -= 360
        while delta < -180: delta += 360
        instruction = None
        if abs(delta) >= 30:  # belirgin dönüş
            instruction = "sağa dönün" if delta > 0 else "sola dönün"
            steps.append({"instruction": instruction, "distance_m": int(total_since_last)})
            total_since_last = 0.0
        prev_bearing = b
        prev_point = cur
    if total_since_last > 0:
        steps.append({"instruction": "düz devam", "distance_m": int(total_since_last)})
    return steps

# -------------------------
# Çok duraklı rota (TSP benzeri): en iyi sıralamayı bul
# -------------------------
def get_cost_matrix(conn, nodes, mode="araba"):
    """
    Verilen node listesi arasındaki tüm çiftlerin mesafelerini (cost)
    tek bir SQL sorgusu ile hesaplar ve sözlük olarak döndürür.
    Dönüş: {(start_id, end_id): cost_meter, ...}
    """
    unique_nodes = list(set(nodes))
    if not unique_nodes:
        return {}
    
    # pgRouting pgr_dijkstra, array parametrelerini destekler.
    # pgr_dijkstra(sql, start_vids, end_vids, directed)
    # Tüm noktalar arası mesafe matrisini tek seferde çekeriz.
    
    nodes_table, edges_table = get_routing_tables(mode)
    
    # DEBUG LOG
    print(f"[DEBUG] get_cost_matrix | mode={mode} | table={edges_table} | nodes_count={len(unique_nodes)}")
    
    directed = True
    
    edges_sql = f"SELECT id, source, target, cost, reverse_cost FROM {edges_table}"

    matrix = {}
    with conn.cursor() as cur:
        query = f"""
            SELECT start_vid, end_vid, agg_cost
            FROM pgr_dijkstra(
                %s,
                %s,
                %s,
                directed := %s
            );
        """
        cur.execute(query, (edges_sql, unique_nodes, unique_nodes, directed))
        rows = cur.fetchall()
        for r in rows:
            start_id, end_id, cost = r
            matrix[(start_id, end_id)] = float(cost)
            
    return matrix

def compute_best_route_order(conn, start_node, stop_nodes, mode="araba"):
    """
    start_node sabit; stop_nodes listesi ziyaret edilecek düğümler.
    Tüm permütasyonları dener ve toplam mesafesi en kısa olan sırayı döndürür.
    
    Optimasyon: Önce tüm noktalar arası mesafe matrisini (Distance Matrix)
    tek sorguyla alıp belleğe atarız. Sonra permütasyonları Python tarafında
    toplayarak hesaplarız. Bu sayede N! kadar SQL sorgusu yerine 1 sorgu atarız.
    """
    print(f"[DEBUG] compute_best_route_order | mode={mode} | start={start_node} | stops={stop_nodes}")
    
    best_perm = None
    best_cost = None
    
    # 1) Mesafe Matrisini Hazırla
    # Hesaplanacak tüm noktalar: start_node + stop_nodes
    all_nodes = [start_node] + stop_nodes
    cost_matrix = get_cost_matrix(conn, all_nodes, mode=mode)

    # 2) Permütasyonları dene
    for perm in permutations(stop_nodes):
        total_cost = 0.0
        current = start_node
        feasible = True

        for nxt in perm:
            # Matristen maliyeti çek
            # (current, nxt) çifti matriste yoksa yol yok demektir (veya aynı noktadır)
            if current == nxt:
                step_cost = 0.0
            else:
                step_cost = cost_matrix.get((current, nxt))
            
            if step_cost is None:
                feasible = False
                break
            
            total_cost += step_cost
            current = nxt

        if feasible and (best_cost is None or total_cost < best_cost):
            best_cost = total_cost
            best_perm = perm

    return best_perm, best_cost


# ======================================================
# 1) Ana sayfa: En Kısa Yol (2 nokta)
# ======================================================
@app.route("/", methods=["GET", "POST"])
def index():
    db_ok = False
    db_message = ""
    route_url = None
    error_message = None
    total_distance_km = None
    estimated_time_min = None
    conn = None

    # Veritabani baglantisini test et
    conn, db_ok, db_message, db_error = init_db_connection()
    if db_error:
        error_message = db_error
        try:
            m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12, conn=conn if conn else None)
            route_url = save_map_html(m, "route_map.html", "show_route_map")
        except Exception:
            pass
        route_url = route_url or url_for("show_route_map")
        return render_template(
            "index.html",
            db_ok=db_ok,
            db_message=db_message,
            route_url=route_url,
            error_message=error_message,
            total_distance_km=total_distance_km,
            estimated_time_min=estimated_time_min
        )

    try:
        m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12, conn=conn)
        route_url = save_map_html(m, "route_map.html", "show_route_map")
    except Exception as e:
        db_ok = False
        error_message = format_db_error(e)
        try:
            m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12, conn=conn if conn else None)
            route_url = save_map_html(m, "route_map.html", "show_route_map")
        except Exception:
            pass
        route_url = route_url or url_for("show_route_map")
        close_conn(conn)
        return render_template(
            "index.html",
            db_ok=db_ok,
            db_message=db_message,
            route_url=route_url,
            error_message=error_message,
            total_distance_km=total_distance_km,
            estimated_time_min=estimated_time_min
        )

    # En kısa yol formu gönderildiyse
    if request.method == "POST":
        try:
            # 1) Formdan verileri al
            start_place = request.form.get("start_place", "").strip()
            end_place = request.form.get("end_place", "").strip()

            start_lat_str = request.form.get("start_lat", "").strip()
            start_lon_str = request.form.get("start_lon", "").strip()
            end_lat_str = request.form.get("end_lat", "").strip()
            end_lon_str = request.form.get("end_lon", "").strip()

            # Başlangıç noktası: adres varsa öncelikle geocode et; gerekirse koordinata düş
            start_lat = None
            start_lon = None

            if start_place:
                geo = geocode_place(start_place)
                if geo:
                    start_lat, start_lon = geo
                else:
                    if start_lat_str and start_lon_str:
                        start_lat = float(start_lat_str)
                        start_lon = float(start_lon_str)
                    else:
                        error_message = f"Başlangıç için bu isimle konum bulunamadı: {start_place}"
            else:
                if start_lat_str and start_lon_str:
                    start_lat = float(start_lat_str)
                    start_lon = float(start_lon_str)
                else:
                    error_message = "Başlangıç için semt/adres girilmelidir."

            # Bitiş noktası: adres varsa öncelikle geocode et; gerekirse koordinata düş
            end_lat = None
            end_lon = None

            if end_place:
                geo = geocode_place(end_place)
                if geo:
                    end_lat, end_lon = geo
                else:
                    if end_lat_str and end_lon_str:
                        end_lat = float(end_lat_str)
                        end_lon = float(end_lon_str)
                    else:
                        error_message = f"Bitiş için bu isimle konum bulunamadı: {end_place}"
            else:
                if end_lat_str and end_lon_str:
                    end_lat = float(end_lat_str)
                    end_lon = float(end_lon_str)
                else:
                    if not error_message:
                        error_message = "Bitiş için semt/adres girilmelidir."

            if error_message:
                close_conn(conn)
                return render_template(
                    "index.html",
                    db_ok=db_ok,
                    db_message=db_message,
                    route_url=route_url,
                    error_message=error_message
                )

            # 2) En yakın node'ları bul
            start_node = find_nearest_node(conn, start_lat, start_lon)
            end_node = find_nearest_node(conn, end_lat, end_lon)

            if start_node is None or end_node is None:
                error_message = "Başlangıç veya bitiş için en yakın düğüm bulunamadı."
            else:
                wkts = get_route_geom_wkts(conn, start_node, end_node)

                if not wkts:
                    error_message = "Bu iki nokta arasında rota bulunamadı."
                else:
                    cost_m = get_shortest_path_cost(conn, start_node, end_node)
                    if cost_m is not None:
                        total_distance_km = round(cost_m / 1000.0, 2)
                        avg_speed_kmh = get_avg_speed_kmh()
                        estimated_time_min = int(round((total_distance_km / avg_speed_kmh) * 60.0))
                    all_coords = []
                    for wkt in wkts:
                        coords = linestring_wkt_to_latlon_list(wkt)
                        all_coords.extend(coords)

                    m = create_offline_map(location=[start_lat, start_lon], zoom_start=12, conn=conn)
                    folium.Marker(
                        [start_lat, start_lon],
                        tooltip=f"Başlangıç - {start_place if start_place else f'({start_lat}, {start_lon})'}",
                        icon=folium.Icon(color="green", icon="info-sign")
                    ).add_to(m)
                    folium.Marker(
                        [end_lat, end_lon],
                        tooltip=f"Bitiş - {end_place if end_place else f'({end_lat}, {end_lon})'}",
                        icon=folium.Icon(color="red", icon="info-sign")
                    ).add_to(m)
                    folium.PolyLine(all_coords, tooltip="En Kısa Yol").add_to(m)
                    bounds_coords = list(all_coords)
                    bounds_coords.append((start_lat, start_lon))
                    bounds_coords.append((end_lat, end_lon))
                    fit_bounds_from_coords(m, bounds_coords)

                    route_url = save_map_html(m, "route_map.html", "show_route_map")

        except Exception as e:
            error_message = f"Rota hesaplanırken hata oluştu: {e}"

        finally:
            close_conn(conn)
    else:
        close_conn(conn)

    return render_template(
        "index.html",
        db_ok=db_ok,
        db_message=db_message,
        route_url=route_url,
        error_message=error_message,
        total_distance_km=total_distance_km,
        estimated_time_min=estimated_time_min
    )


@app.route("/route_map")
def show_route_map():
    return render_template("route_map.html")


# ======================================================
# 2) Hizmet Alanı (Hastane merkezli Service Area)
# ======================================================
@app.route("/service_area", methods=["GET", "POST"])
def service_area():
    """
    Modül 2: Hizmet Alanı Analizi
    - Kullanıcı bir hastane seçer (pois.category = 'hastane')
    - Yarıçap (km) seçer
    - İsterse belirli bir kategori (metro, otobus, market, vb.) seçer
    - Bu sınır içinde kalan POI'lar hem haritada gösterilir hem de
      kategori bazlı istatistik üretilir.
    """
    db_ok = False
    db_message = ""
    error_message = None
    service_area_map_url = None
    stats = []
    poi_results = []
    hospitals = []
    selected_categories = []

    # Global stilleri kopyala ve havalimanını çıkar (Bu modülde istenmiyor)
    cat_styles = CAT_STYLES.copy()
    if "havalimani" in cat_styles:
        del cat_styles["havalimani"]

    conn, db_ok, db_message, db_error = init_db_connection()
    if db_error:
        error_message = db_error
        return render_template(
            "service_area.html",
            db_ok=db_ok,
            db_message=db_message,
            error_message=error_message,
            service_area_map_url=service_area_map_url,
            stats=stats,
            poi_results=poi_results,
            hospitals=hospitals,
            selected_categories=selected_categories,
            cat_styles=CAT_STYLES
        )

    try:
        with conn.cursor() as cur:
            # Hastane listesini cek (dropdown icin)
            cur.execute(
                "SELECT id, name, district, ST_AsText(geom) AS wkt "
                "FROM pois "
                "WHERE category = 'hastane' "
                "ORDER BY district, name;"
            )
            rows = cur.fetchall()
            for r in rows:
                hid, hname, hdistrict, hwkt = r
                hospitals.append({
                    "id": hid,
                    "name": hname,
                    "district": hdistrict
                })
    except Exception as e:
        error_message = format_db_error(e)
        close_conn(conn)
        return render_template(
            "service_area.html",
            db_ok=db_ok,
            db_message=db_message,
            error_message=error_message,
            service_area_map_url=service_area_map_url,
            stats=stats,
            poi_results=poi_results,
            hospitals=hospitals,
            selected_categories=selected_categories,
            cat_styles=CAT_STYLES
        )

    if request.method == "POST":
        mode = request.form.get("mode", "radius")
    else:
        mode = request.args.get("mode", "radius")
    
    if request.method == "POST":
        hospital_id = request.form.get("hospital_id", "").strip()
        distance_km = request.form.get("distance_km", "5").strip()
        selected_categories = [c.strip() for c in request.form.getlist("category_filter") if c.strip()]
        drawing_data = request.form.get("drawing_data", "").strip()

        if mode == "radius":
            # --- MEVCUT YARIÇAP MANTIĞI ---
            if not hospital_id:
                error_message = "Lütfen bir hastane seçin."
            else:
                try:
                    distance_km = float(distance_km)
                    distance_m = distance_km * 1000.0
                except ValueError:
                    distance_km = 5.0
                    distance_m = 5000.0

                try:
                    with conn.cursor() as cur:
                        # 1) Seçilen hastanenin konumu
                        cur.execute("""
                            SELECT name, district, geom, ST_AsText(geom) AS wkt
                            FROM pois
                            WHERE id = %s AND category = 'hastane';
                        """, (hospital_id,))
                        hospital_row = cur.fetchone()

                        if not hospital_row:
                            error_message = "Seçilen hastane veritabanında bulunamadı."
                        else:
                            h_name, h_district, h_geom, h_wkt = hospital_row
                            h_lat, h_lon = point_wkt_to_latlon(h_wkt)

                            # 2) İstatistik
                            stats_sql = """
                                SELECT category, COUNT(*)
                                FROM pois
                                WHERE ST_DWithin(
                                    geom::geography,
                                    %s::geography,
                                    %s
                                )
                            """
                            params_stats = [h_geom, distance_m]

                            if selected_categories:
                                placeholders = ",".join(["%s"] * len(selected_categories))
                                stats_sql += f" AND category IN ({placeholders})"
                                params_stats.extend(selected_categories)

                            stats_sql += " GROUP BY category ORDER BY category;"

                            cur.execute(stats_sql, tuple(params_stats))
                            stat_rows = cur.fetchall()
                            for cat, cnt in stat_rows:
                                cat = normalize_poi_category(cat)
                                stats.append({
                                    "category": cat,
                                    "count": cnt,
                                    "key": make_category_key(cat),
                                })

                            # 3) Detay liste
                            poi_sql = """
                                SELECT name, category, district, ST_AsText(geom) AS wkt,
                                       ST_Distance(geom::geography, %s::geography) as dist_m
                                FROM pois
                                WHERE ST_DWithin(
                                    geom::geography,
                                    %s::geography,
                                    %s
                                )
                            """
                            params_poi = [h_geom, h_geom, distance_m]

                            if selected_categories:
                                placeholders = ",".join(["%s"] * len(selected_categories))
                                poi_sql += f" AND category IN ({placeholders})"
                                params_poi.extend(selected_categories)

                            poi_sql += " ORDER BY dist_m ASC LIMIT 1000;"

                            cur.execute(poi_sql, tuple(params_poi))
                            poi_rows = cur.fetchall()
                            for r in poi_rows:
                                nm, cat, dist, wkt, distance_val = r
                                cat = normalize_poi_category(cat)
                                lat, lon = point_wkt_to_latlon(wkt)
                                
                                # Mesafe formatlama (örn: 1.2 km veya 850 m)
                                if distance_val >= 1000:
                                    dist_str = f"{distance_val/1000:.2f} km"
                                else:
                                    dist_str = f"{int(distance_val)} m"

                                poi_results.append({
                                    "name": nm,
                                    "category": cat,
                                    "district": dist,
                                    "lat": lat,
                                    "lon": lon,
                                    "distance_str": dist_str,
                                    "distance_m": float(distance_val)
                                })

                            # 4) Harita (Radius)
                            m = create_offline_map(location=[h_lat, h_lon], zoom_start=13, conn=conn)

                            folium.Marker(
                                [h_lat, h_lon],
                                tooltip=f"MERKEZ: {h_name}",
                                popup=f"<b>MERKEZ NOKTA</b><br>{h_name}<br>{h_district}",
                                icon=folium.Icon(color="black", icon="star", prefix="fa", icon_color="white"),
                                z_index_offset=1000
                            ).add_to(m)

                            folium.CircleMarker(
                                location=[h_lat, h_lon],
                                radius=10,
                                color="black",
                                weight=2,
                                fill=True,
                                fill_color="black",
                                fill_opacity=0.2
                            ).add_to(m)

                            folium.Circle(
                                location=[h_lat, h_lon],
                                radius=distance_m,
                                color="blue",
                                fill=True,
                                fill_opacity=0.1,
                                tooltip=f"{distance_km} km Hizmet Alanı"
                            ).add_to(m)

                            for item in poi_results:
                                c_cat = item['category']
                                popup_text = f"{item['name']} ({item['category']}, {item['district']})"
                                folium.Marker(
                                    [item["lat"], item["lon"]],
                                    tooltip=popup_text,
                                    popup=popup_text,
                                    icon=build_poi_div_icon(c_cat, styles=cat_styles)
                                ).add_to(m)

                            bounds_coords = [(h_lat, h_lon)]
                            bounds_coords.extend([(item["lat"], item["lon"]) for item in poi_results])
                            fit_bounds_from_coords(m, bounds_coords)

                            # Çizim aracını yine de ekleyelim, belki kullanıcı yeni çizim yapmak ister
                            Draw(
                                draw_options={
                                    'polyline': False,
                                    'rectangle': True,
                                    'polygon': True,
                                    'circle': False,
                                    'marker': False,
                                    'circlemarker': False
                                },
                                edit_options={'edit': False}
                            ).add_to(m)
                            inject_map_draw_js(m)
                            inject_map_focus_js(m)
                            inject_map_toggle_draw_js(m)

                            service_area_map_url = save_map_html(
                                m,
                                "service_area_map.html",
                                "show_service_area_map",
                            )

                            if poi_results:
                                poi_results = group_poi_results_by_category(poi_results)

                except Exception as e:
                    error_message = f"Yarıçap analizi hatası: {e}"
                finally:
                    close_conn(conn)

        elif mode == "drawing":
            # --- ÇİZİM İLE SORGULAMA MANTIĞI ---
            if not drawing_data:
                error_message = "Lütfen harita üzerinde bir alan çizin."
                close_conn(conn)
            else:
                try:
                    # Gelen veriyi parse edip Geometry kısmını alalım
                    # Çünkü Leaflet.Draw "Feature" dönerken PostGIS ST_GeomFromGeoJSON bazen saf Geometry bekleyebilir
                    # veya Feature içindeki properties kısmı sorun çıkarabilir.
                    geo_obj = json.loads(drawing_data)
                    
                    # Eğer Feature ise geometry'sini al
                    if geo_obj.get('type') == 'Feature' and 'geometry' in geo_obj:
                        geo_obj = geo_obj['geometry']
                    
                    # Tekrar string yap
                    clean_geojson = json.dumps(geo_obj)

                    with conn.cursor() as cur:
                        # 1) İstatistik
                        # ST_GeomFromGeoJSON ile gelen JSON verisini geometriye çeviriyoruz
                        stats_sql = """
                            SELECT category, COUNT(*)
                            FROM pois
                            WHERE ST_Within(
                                geom,
                                ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
                            )
                        """
                        params_stats = [clean_geojson]

                        if selected_categories:
                            placeholders = ",".join(["%s"] * len(selected_categories))
                            stats_sql += f" AND category IN ({placeholders})"
                            params_stats.extend(selected_categories)

                        stats_sql += " GROUP BY category ORDER BY category;"

                        cur.execute(stats_sql, tuple(params_stats))
                        stat_rows = cur.fetchall()
                        for cat, cnt in stat_rows:
                            cat = normalize_poi_category(cat)
                            stats.append({
                                "category": cat,
                                "count": cnt,
                                "key": make_category_key(cat),
                            })

                        # 2) Detay liste
                        poi_sql = """
                            SELECT name, category, district, ST_AsText(geom) AS wkt
                            FROM pois
                            WHERE ST_Within(
                                geom,
                                ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
                            )
                        """
                        params_poi = [clean_geojson]

                        if selected_categories:
                            placeholders = ",".join(["%s"] * len(selected_categories))
                            poi_sql += f" AND category IN ({placeholders})"
                            params_poi.extend(selected_categories)

                        # Hastaneleri öncelikli getir
                        poi_sql += " ORDER BY (category='hastane') DESC, category, district, name LIMIT 1000;"

                        cur.execute(poi_sql, tuple(params_poi))
                        poi_rows = cur.fetchall()
                        
                        # Harita merkezi için ortalama koordinat bulalım
                        lat_sum, lon_sum, count = 0, 0, 0

                        for r in poi_rows:
                            nm, cat, dist, wkt = r
                            cat = normalize_poi_category(cat)
                            lat, lon = point_wkt_to_latlon(wkt)
                            poi_results.append({
                                "name": nm,
                                "category": cat,
                                "district": dist,
                                "lat": lat,
                                "lon": lon
                            })
                            lat_sum += lat
                            lon_sum += lon
                            count += 1
                        
                        center_lat, center_lon = 41.015137, 28.979530 # Default
                        if count > 0:
                            center_lat = lat_sum / count
                            center_lon = lon_sum / count

                        # 3) Harita (Drawing)
                        m = create_offline_map(location=[center_lat, center_lon], zoom_start=13, conn=conn)

                        # Kullanıcının çizdiği alanı haritaya geri ekleyelim (GeoJSON olarak)
                        # Not: Haritada göstermek için orijinal drawing_data veya clean_geojson kullanılabilir.
                        folium.GeoJson(
                            geo_obj,
                            name="Çizilen Alan",
                            style_function=lambda x: {'color': 'red', 'fillColor': 'red', 'weight': 2, 'fillOpacity': 0.1}
                        ).add_to(m)

                        for item in poi_results:
                            c_cat = item['category']
                            popup_text = f"{item['name']} ({item['category']}, {item['district']})"
                            folium.Marker(
                                [item["lat"], item["lon"]],
                                tooltip=popup_text,
                                popup=popup_text,
                                icon=build_poi_div_icon(c_cat, styles=cat_styles)
                            ).add_to(m)

                        bounds_coords = [(center_lat, center_lon)]
                        bounds_coords.extend([(item["lat"], item["lon"]) for item in poi_results])
                        fit_bounds_from_coords(m, bounds_coords)

                        # Çizim aracını ekle
                        Draw(
                            draw_options={
                                'polyline': False,
                                'rectangle': True,
                                'polygon': True,
                                'circle': False,
                                'marker': False,
                                'circlemarker': False
                            },
                            edit_options={'edit': False}
                        ).add_to(m)
                        inject_map_draw_js(m)
                        inject_map_focus_js(m)
                        inject_map_toggle_draw_js(m)

                        service_area_map_url = save_map_html(
                            m,
                            "service_area_map.html",
                            "show_service_area_map",
                        )

                        if poi_results:
                            poi_results = group_poi_results_by_category(poi_results)

                except Exception as e:
                    error_message = f"Çizim alanı analizi hatası: {e}"
                finally:
                    close_conn(conn)

    else:
        close_conn(conn)
        try:
            m = create_offline_map(location=[41.015137, 28.979530], zoom_start=12)
            
            # Çizim aracını ekle (GET isteğinde de görünsün)
            Draw(
                draw_options={
                    'polyline': False,
                    'rectangle': True,
                    'polygon': True,
                    'circle': False,
                    'marker': False,
                    'circlemarker': False
                },
                edit_options={'edit': False}
            ).add_to(m)
            inject_map_draw_js(m)
            
            inject_map_focus_js(m)
            inject_map_toggle_draw_js(m)
            
            service_area_map_url = save_map_html(
                m,
                "service_area_map.html",
                "show_service_area_map",
            )
        except Exception:
            pass

    return render_template(
        "service_area.html",
        db_ok=db_ok,
        db_message=db_message,
        error_message=error_message,
        service_area_map_url=service_area_map_url,
        stats=stats,
        poi_results=poi_results,
        hospitals=hospitals,
        selected_categories=selected_categories,
        cat_styles=cat_styles,
        mode=mode # Mod bilgisini geri dön
    )




@app.route("/service_area_map")
def show_service_area_map():
    return render_template("service_area_map.html")


# ======================================================
# 3) Çok Noktalı Rota (1 başlangıç + 1–5 durak)
# ======================================================
@app.route("/multi_route", methods=["GET", "POST"])
def multi_route():
    db_ok = False
    db_message = ""
    multi_route_url = None
    error_message = None
    best_order_info = None
    estimated_time_min = None
    total_distance_km = None
    start_label = None # Başlangıç noktası etiketini saklamak için
    
    # DB testi
    conn, db_ok, db_message, db_error = init_db_connection()
    if db_error:
        error_message = db_error
        try:
            m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12, conn=conn if conn else None)
            multi_route_url = save_map_html(m, "multi_route_map.html", "show_multi_route_map")
        except Exception:
            pass
        return render_template(
            "multi_route.html",
            db_ok=db_ok,
            db_message=db_message,
            multi_route_url=multi_route_url,
            error_message=error_message,
            best_order_info=best_order_info,
            total_distance_km=total_distance_km,
            estimated_time_min=estimated_time_min,
            start_label=start_label
        )

    try:
        m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12, conn=conn)
        multi_route_url = save_map_html(m, "multi_route_map.html", "show_multi_route_map")
    except Exception:
        pass

    if request.method == "POST":
        try:
            # Ulaşım modu
            mode = request.form.get("mode", "araba").strip()
            
            # DEBUG LOG
            print(f"[DEBUG] Route: /multi_route (POST) | mode={mode}")

            # Başlangıç noktası (depo)
            start_place = request.form.get("start_place", "").strip()
            start_lat_str = request.form.get("start_lat", "").strip()
            start_lon_str = request.form.get("start_lon", "").strip()

            start_lat = None
            start_lon = None
            start_label = ""

            if start_lat_str and start_lon_str:
                start_lat = float(start_lat_str)
                start_lon = float(start_lon_str)
                start_label = f"Koordinat ({start_lat}, {start_lon})"
            elif start_place:
                geo = geocode_place(start_place)
                if geo:
                    start_lat, start_lon = geo
                    start_label = start_place
                else:
                    error_message = f"Başlangıç için bu isimle konum bulunamadı: {start_place}"
            else:
                error_message = "Başlangıç noktası için semt/adres veya enlem-boylam girilmelidir."

            if error_message:
                close_conn(conn)
                return render_template(
                    "multi_route.html",
                    db_ok=db_ok,
                    db_message=db_message,
                    multi_route_url=multi_route_url,
                    error_message=error_message,
                    best_order_info=best_order_info,
                    total_distance_km=total_distance_km,
                    estimated_time_min=estimated_time_min,
                    start_label=start_label
                )

            start_node = find_nearest_node(conn, start_lat, start_lon, mode=mode)
            if start_node is None:
                error_message = "Başlangıç noktası için en yakın düğüm bulunamadı."
                close_conn(conn)
                return render_template(
                    "multi_route.html",
                    db_ok=db_ok,
                    db_message=db_message,
                    multi_route_url=multi_route_url,
                    error_message=error_message,
                    best_order_info=best_order_info,
                    total_distance_km=total_distance_km,
                    estimated_time_min=estimated_time_min,
                    start_label=start_label
                )

            # Teslim noktaları (max 5)
            stops = []  # her biri: { 'label', 'lat', 'lon', 'node' }

            for i in range(1, 6):  # stop1 ... stop5
                place_key = f"stop{i}_place"
                lat_key = f"stop{i}_lat"
                lon_key = f"stop{i}_lon"

                place = request.form.get(place_key, "").strip()
                lat_str = request.form.get(lat_key, "").strip()
                lon_str = request.form.get(lon_key, "").strip()

                if not place and not (lat_str and lon_str):
                    # Bu durak boş bırakılmış, atla
                    continue

                # Koordinat öncelikli, yoksa geocode
                lat = None
                lon = None
                label = ""

                if lat_str and lon_str:
                    lat = float(lat_str)
                    lon = float(lon_str)
                    label = f"Durak {i} (Koordinat)"
                elif place:
                    geo = geocode_place(place)
                    if geo:
                        lat, lon = geo
                        label = f"Durak {i} - {place}"
                    else:
                        error_message = f"Durak {i} için bu isimle konum bulunamadı: {place}"
                        break
                else:
                    continue

                node_id = find_nearest_node(conn, lat, lon, mode=mode)
                if node_id is None:
                    error_message = f"Durak {i} için en yakın düğüm bulunamadı."
                    break

                stops.append({
                    "label": label,
                    "lat": lat,
                    "lon": lon,
                    "node": node_id
                })

            if error_message:
                close_conn(conn)
                return render_template(
                    "multi_route.html",
                    db_ok=db_ok,
                    db_message=db_message,
                    multi_route_url=multi_route_url,
                    error_message=error_message,
                    best_order_info=best_order_info,
                    total_distance_km=total_distance_km,
                    estimated_time_min=estimated_time_min,
                    start_label=start_label
                )

            if len(stops) < 1:
                error_message = "En az 1 adet teslim/ziyaret noktası girilmelidir."
                close_conn(conn)
                return render_template(
                    "multi_route.html",
                    db_ok=db_ok,
                    db_message=db_message,
                    multi_route_url=multi_route_url,
                    error_message=error_message,
                    best_order_info=best_order_info,
                    total_distance_km=total_distance_km,
                    estimated_time_min=estimated_time_min,
                    start_label=start_label
                )

            # Node listesini ve mapping'i hazırlayalım
            stop_nodes = [s["node"] for s in stops]
            node_to_info = {s["node"]: s for s in stops}

            # En iyi sıralamayı hesapla
            best_perm_nodes, best_cost = compute_best_route_order(conn, start_node, stop_nodes, mode=mode)

            if best_perm_nodes is None:
                error_message = "Girilen noktalar için uygun bir rota bulunamadı."
                close_conn(conn)
                return render_template(
                    "multi_route.html",
                    db_ok=db_ok,
                    db_message=db_message,
                    multi_route_url=multi_route_url,
                    error_message=error_message,
                    best_order_info=best_order_info,
                    total_distance_km=total_distance_km,
                    estimated_time_min=estimated_time_min,
                    start_label=start_label
                )

            # En iyi sıraya göre durak bilgisini çıkar
            best_order_info = []
            for idx, node_id in enumerate(best_perm_nodes, start=1):
                info = node_to_info[node_id]
                best_order_info.append({
                    "step": idx,
                    "label": info["label"],
                    "lat": info["lat"],
                    "lon": info["lon"]
                })

            # Toplam mesafe (metreden km'ye)
            total_distance_km = round(best_cost / 1000.0, 2) if best_cost is not None else None
            
            # Toplam süre (dk)
            estimated_time_min = None
            if total_distance_km is not None:
                avg_speed_kmh = get_avg_speed_kmh(mode=mode)
                estimated_time_min = int(round((total_distance_km / avg_speed_kmh) * 60.0))

            # Harita üret: başlangıç + duraklar + rota
            all_wkts = []
            current_node = start_node

            for node_id in best_perm_nodes:
                seg_wkts = get_route_geom_wkts(conn, current_node, node_id, mode=mode)
                all_wkts.extend(seg_wkts)
                current_node = node_id

            all_coords = []
            for wkt in all_wkts:
                coords = linestring_wkt_to_latlon_list(wkt)
                all_coords.extend(coords)

            # Harita merkezi olarak başlangıç noktası
            m = create_offline_map(location=[start_lat, start_lon], zoom_start=12, conn=conn)
            
            # Başlangıç Noktası (B) - Yeşil
            folium.Marker(
                [start_lat, start_lon], 
                tooltip=f"Başlangıç - {start_label}",
                icon=folium.DivIcon(
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                    html="""
                        <div style="
                            background-color: #28a745; 
                            color: white; 
                            width: 30px; 
                            height: 30px; 
                            border-radius: 50%; 
                            display: flex; 
                            align-items: center; 
                            justify-content: center; 
                            font-weight: bold; 
                            font-family: Arial, sans-serif;
                            border: 2px solid white; 
                            box-shadow: 0 2px 5px rgba(0,0,0,0.5);
                        ">B</div>
                    """
                )
            ).add_to(m)

            # Durak işaretleri (sıraya göre numaralı) - Mavi
            for info in best_order_info:
                folium.Marker(
                    [info["lat"], info["lon"]],
                    tooltip=f"{info['step']}. Durak - {info['label']}",
                    icon=folium.DivIcon(
                        icon_size=(30, 30),
                        icon_anchor=(15, 15),
                        html=f"""
                            <div style="
                                background-color: #007bff; 
                                color: white; 
                                width: 30px; 
                                height: 30px; 
                                border-radius: 50%; 
                                display: flex; 
                                align-items: center; 
                                justify-content: center; 
                                font-weight: bold; 
                                font-family: Arial, sans-serif;
                                border: 2px solid white; 
                                box-shadow: 0 2px 5px rgba(0,0,0,0.5);
                            ">{info['step']}</div>
                        """
                    )
                ).add_to(m)

            # Rota çizgisi
            if all_coords:
                line_color = "green" if mode == "yaya" else "blue"
                dash_array = "5, 10" if mode == "yaya" else None
                folium.PolyLine(all_coords, tooltip="Optimum Rota", color=line_color, weight=5, dash_array=dash_array).add_to(m)
            bounds_coords = list(all_coords)
            bounds_coords.append((start_lat, start_lon))
            for info in best_order_info:
                bounds_coords.append((info["lat"], info["lon"]))
            fit_bounds_from_coords(m, bounds_coords)

            multi_route_url = save_map_html(m, "multi_route_map.html", "show_multi_route_map")


        except Exception as e:
            error_message = f"Çok noktalı rota hesaplanırken hata oluştu: {e}"

        finally:
            close_conn(conn)

    return render_template(
        "multi_route.html",
        db_ok=db_ok,
        db_message=db_message,
        multi_route_url=multi_route_url,
        error_message=error_message,
        best_order_info=best_order_info,
        total_distance_km=total_distance_km,
        estimated_time_min=estimated_time_min,
        start_label=start_label
    )


@app.route("/multi_route_map")
def show_multi_route_map():
    return render_template("multi_route_map.html")


# ======================================================
# 4) POI Arama
# ======================================================
@app.route("/pois", methods=["GET", "POST"])
def pois():
    """
    POI Arama Modülü:
    PostGIS içindeki 'pois' tablosundan
    kategori + ilçe + isim filtresi ile veri çeker ve
    harita + liste olarak gösterir.
    """
    db_ok = False
    db_message = ""
    poi_map_url = None
    error_message = None
    results = []
    districts = []
    selected_categories = []
    stats = []
    conn = None

    try:
        conn, db_ok, db_message, db_error = init_db_connection()
        if db_error:
            error_message = db_error
            try:
                m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12)
                inject_map_focus_js(m)
                poi_map_url = save_map_html(
                    m,
                    "pois_map.html",
                    "show_pois_map",
                    v=time.time(),
                )
            except Exception:
                pass
            return render_template(
                "pois.html",
                db_ok=db_ok,
                db_message=db_message,
                poi_map_url=poi_map_url,
                error_message=error_message,
                results=results,
                districts=districts,
                selected_categories=selected_categories,
                cat_styles=CAT_STYLES,
                stats=stats
            )

        # Statik ilce listesi
        districts = [
            "Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler", 
            "Bakırköy", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beykoz", "Beylikdüzü", 
            "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler", "Esenyurt", 
            "Eyüpsultan", "Fatih", "Gaziosmanpaşa", "Güngören", "Kadıköy", "Kağıthane", 
            "Kartal", "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer", 
            "Silivri", "Sultanbeyli", "Sultangazi", "Şile", "Şişli", "Tuzla", 
            "Ümraniye", "Üsküdar", "Zeytinburnu"
        ]
        district_name_map = {normalize_tr_basic(d): d for d in districts}
        overrides = load_poi_district_overrides()
        override_lookup = {
            (o["category"], o["name_norm"]): district_name_map.get(
                o["district_norm"], o["district_norm"].title()
            )
            for o in overrides
        }
        if request.method == "POST":
            selected_categories = [c.strip() for c in request.form.getlist("category_filter") if c.strip()]
            name_filter = request.form.get("name_filter", "").strip()
            district = request.form.get("district", "").strip()
            district, name_filter, normalized_name_filter = resolve_district_from_name_filter(
                districts, district, name_filter
            )
            boundary_geojson = None
            boundary_coords = []
            map_bounds_override = None
            override_matches = []
            if district:
                district_norm = normalize_tr_basic(district)
                override_matches = [
                    (o["category"], o["name_norm"])
                    for o in overrides
                    if o["district_norm"] == district_norm
                ]

            with conn.cursor() as cur:
                has_boundary, boundary_name = resolve_district_boundary(cur, district)
                
                # Sınır verisini DB veya dosyadan al (Harita gösterimi için)
                boundary_geojson = get_district_geojson(conn, district)
                # GeoJSON içinden sadece geometriyi al (filtreleme için)
                custom_geometry = None
                if boundary_geojson:
                    if boundary_geojson.get("type") == "FeatureCollection" and boundary_geojson.get("features"):
                        custom_geometry = boundary_geojson["features"][0]["geometry"]
                    elif boundary_geojson.get("type") == "Feature":
                        custom_geometry = boundary_geojson["geometry"]
                    elif boundary_geojson.get("type") in ["Polygon", "MultiPolygon"]:
                        custom_geometry = boundary_geojson
                boundary_coords = extract_geojson_latlon(boundary_geojson)
                if boundary_coords:
                    tile_bounds = get_offline_tile_bounds() or [[40.80, 28.50], [41.30, 29.45]]
                    map_bounds_override = merge_bounds(tile_bounds, bounds_from_coords(boundary_coords))

                base_query = """
                    SELECT name, category, district, ST_AsText(geom) AS wkt
                    FROM pois
                    WHERE 1=1
                """
                params = []
                base_query, params = apply_pois_filters(
                    base_query,
                    params,
                    selected_categories,
                    district,
                    name_filter,
                    normalized_name_filter,
                    has_boundary,
                    boundary_name,
                    custom_geojson_geometry=custom_geometry,
                    district_overrides=override_matches,
                    use_district_label=False,
                )

                cur.execute(base_query, tuple(params))
                rows = cur.fetchall()

                # --- ISTATISTIK SORGUSU ---
                stats_query = """
                    SELECT category, COUNT(*)
                    FROM pois
                    WHERE 1=1
                """
                stats_params = []
                stats_query, stats_params = apply_pois_filters(
                    stats_query,
                    stats_params,
                    selected_categories,
                    district,
                    name_filter,
                    normalized_name_filter,
                    has_boundary,
                    boundary_name,
                    custom_geojson_geometry=custom_geometry,
                    district_overrides=override_matches,
                    use_district_label=True,
                )

                stats_query += " GROUP BY category ORDER BY COUNT(*) DESC;"

                cur.execute(stats_query, tuple(stats_params))
                stat_rows = cur.fetchall()
                
                for cat, cnt in stat_rows:
                    cat = normalize_poi_category(cat)
                    
                    found = False
                    for s in stats:
                        if s["category"] == cat:
                            s["count"] += cnt
                            found = True
                            break
                    if not found:
                        stats.append({
                            "category": cat,
                            "count": cnt,
                            "key": make_category_key(cat),
                        })

            if not rows:
                error_message = "Seçilen kriterlere göre POI kaydı bulunamadı."
                # Sonuç yoksa varsayılan harita
                m = create_offline_map(
                    location=[41.015137, 28.97953],
                    zoom_start=12,
                    max_bounds_override=map_bounds_override,
                )
                add_district_boundary(m, boundary_geojson)
                if boundary_coords:
                    fit_bounds_from_coords(
                        m, boundary_coords, bounds_limit=map_bounds_override
                    )
            else:
                for r in rows:
                    nm, cat, dist, wkt = r
                    cat = normalize_poi_category(cat)
                    override_district = override_lookup.get(
                        (cat, normalize_tr_basic(nm))
                    )
                    if override_district:
                        dist = override_district

                    lat, lon = point_wkt_to_latlon(wkt)
                    
                    if dist is None or dist == 'None':
                        dist = ""
                        
                    results.append({
                        "name": nm,
                        "category": cat,
                        "district": dist,
                        "lat": lat,
                        "lon": lon,
                        "order_index": (
                            get_marmaray_order_index(nm)
                            if cat == "marmaray"
                            else (
                                get_metrobus_order_index(nm)
                                if cat == "metrobus"
                                else None
                            )
                        ),
                    })

                first = results[0]
                m = create_offline_map(
                    location=[first["lat"], first["lon"]],
                    zoom_start=12,
                    max_bounds_override=map_bounds_override,
                )
                add_district_boundary(m, boundary_geojson)

                for item in results:
                    c_cat = item['category']
                    style = CAT_STYLES.get(c_cat, {"color": "gray", "icon": "info", "prefix": "fa"})
                    popup_text = f"{item['name']} ({item['category']}, {item['district']})"
                    css_color = style.get("css", style.get("color", "gray"))
                    icon_html = f"""
                        <div style="
                            background-color: {css_color};
                            color: white;
                            width: 28px;
                            height: 28px;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            box-shadow: 0 1px 4px rgba(0,0,0,0.4);
                            border: 2px solid white;
                        ">
                            <i class="{style.get('prefix', 'fa')} fa-{style.get('icon', 'info')}"></i>
                        </div>
                    """
                    
                    folium.Marker(
                        [item["lat"], item["lon"]],
                        tooltip=popup_text,
                        popup=popup_text,
                        icon=folium.DivIcon(
                            icon_size=(28, 28),
                            icon_anchor=(14, 14),
                            html=icon_html
                        )
                    ).add_to(m)

                map_items = list(results)
                if results:
                    results = group_poi_results_by_category(results)

                bounds_coords = [(item["lat"], item["lon"]) for item in map_items]
                if boundary_coords:
                    bounds_coords.extend(boundary_coords)
                fit_bounds_from_coords(
                    m, bounds_coords, bounds_limit=map_bounds_override
                )

            # Harita kaydetme (Ortak)
            try:
                inject_map_focus_js(m)
                poi_map_url = save_map_html(
                    m,
                    "pois_map.html",
                    "show_pois_map",
                    v=time.time(),
                )
            except Exception as e:
                print(f"Harita kaydetme hatası: {e}")

        else:
            # GET İsteği - Varsayılan Harita
            try:
                m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12)
                inject_map_focus_js(m)
                poi_map_url = save_map_html(
                    m,
                    "pois_map.html",
                    "show_pois_map",
                    v=time.time(),
                )
            except Exception:
                pass

    except Exception as e:
        db_ok = False
        error_message = f"Hata oluştu: {e}"
        try:
            m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12)
            inject_map_focus_js(m)
            poi_map_url = save_map_html(
                m,
                "pois_map.html",
                "show_pois_map",
                v=time.time(),
            )
        except:
            pass
    
    finally:
        close_conn(conn)

    return render_template(
        "pois.html",
        db_ok=db_ok,
        db_message=db_message,
        poi_map_url=poi_map_url,
        error_message=error_message,
        results=results,
        districts=districts,
        selected_categories=selected_categories,
        cat_styles=CAT_STYLES,
        stats=stats
    )



@app.route("/pois_map")
def show_pois_map():
    try:
        map_path = os.path.join(app.root_path, "templates", "pois_map.html")
        with open(map_path, "r", encoding="utf-8") as f:
            html = f.read()
        resp = make_response(html)
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    except Exception:
        return render_template("pois_map.html")

# ======================================================
# 5) Navigasyon (Başlangıç + Bitiş + Ara Nokta)
# ======================================================
@app.route("/navigation", methods=["GET", "POST"])
def navigation():
    db_ok = False
    db_message = ""
    navigation_map_url = None
    error_message = None
    total_distance_km = None
    estimated_time_min = None
    mode = None

    conn, db_ok, db_message, db_error = init_db_connection()
    if db_error:
        error_message = db_error
        try:
            m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12)
            inject_map_click_js(m)
            navigation_map_url = save_map_html(m, "navigation_map.html", "show_navigation_map")
        except Exception:
            pass
        return render_template(
            "navigation.html",
            db_ok=db_ok,
            db_message=db_message,
            navigation_map_url=navigation_map_url,
            error_message=error_message,
            total_distance_km=total_distance_km,
            estimated_time_min=estimated_time_min,
            mode=mode
        )

    try:
        m = create_offline_map(location=[41.015137, 28.97953], zoom_start=12)
        inject_map_click_js(m)
        navigation_map_url = save_map_html(m, "navigation_map.html", "show_navigation_map")
    except Exception:
        pass

    if request.method == "POST":
        try:
            start_place = request.form.get("start_place", "").strip()
            end_place = request.form.get("end_place", "").strip()
            via_place = request.form.get("via_place", "").strip()
            mode = request.form.get("mode", "araba").strip()  # 'araba' or 'yaya'
            speed_profile = request.form.get("speed_profile", "normal").strip()  # 'normal' | 'trafik' | 'gece'
            
            # DEBUG LOG
            print(f"[DEBUG] Route: /navigation (POST) | mode={mode} | start={start_place} | end={end_place}")

            start_lat = None
            start_lon = None
            end_lat = None
            end_lon = None
            via_lat = None
            via_lon = None
            start_lat_str = request.form.get("start_lat", "").strip()
            start_lon_str = request.form.get("start_lon", "").strip()
            end_lat_str = request.form.get("end_lat", "").strip()
            end_lon_str = request.form.get("end_lon", "").strip()
            via_lat_str = request.form.get("via_lat", "").strip()
            via_lon_str = request.form.get("via_lon", "").strip()
            start_node_id_str = request.form.get("start_node_id", "").strip()
            end_node_id_str = request.form.get("end_node_id", "").strip()
            via_node_id_str = request.form.get("via_node_id", "").strip()

            def _parse_node_id(value):
                try:
                    return int(value)
                except Exception:
                    return None

            start_node_id = _parse_node_id(start_node_id_str)
            end_node_id = _parse_node_id(end_node_id_str)
            via_node_id = _parse_node_id(via_node_id_str)

            if start_lat_str and start_lon_str:
                try:
                    start_lat = float(start_lat_str); start_lon = float(start_lon_str)
                except Exception:
                    start_lat = None; start_lon = None
            if start_lat is None or start_lon is None:
                if start_place:
                    geo = geocode_place(start_place)
                    if geo:
                        start_lat, start_lon = geo
                    else:
                        error_message = f"Başlangıç için bu isimle konum bulunamadı: {start_place}"
                else:
                    error_message = "Başlangıç için semt/adres girilmelidir."

            if not error_message:
                if end_lat_str and end_lon_str:
                    try:
                        end_lat = float(end_lat_str); end_lon = float(end_lon_str)
                    except Exception:
                        end_lat = None; end_lon = None
                if end_lat is None or end_lon is None:
                    if end_place:
                        geo = geocode_place(end_place)
                        if geo:
                            end_lat, end_lon = geo
                        else:
                            error_message = f"Bitiş için bu isimle konum bulunamadı: {end_place}"
                    else:
                        error_message = "Bitiş için semt/adres girilmelidir."

            if not error_message and via_place:
                if via_lat_str and via_lon_str:
                    try:
                        via_lat = float(via_lat_str); via_lon = float(via_lon_str)
                    except Exception:
                        via_lat = None; via_lon = None
                if via_lat is None or via_lon is None:
                    geo = geocode_place(via_place)
                    if geo:
                        via_lat, via_lon = geo
                    else:
                        error_message = f"Ara nokta için bu isimle konum bulunamadı: {via_place}"

            if error_message:
                close_conn(conn)
                return render_template(
                    "navigation.html",
                    db_ok=db_ok,
                    db_message=db_message,
                    navigation_map_url=navigation_map_url,
                    error_message=error_message,
                    total_distance_km=total_distance_km,
                    estimated_time_min=estimated_time_min,
                    mode=mode
                )

            # Aday node'ları bul (en yakın 5 node) - Bağlantı kopukluğu riskine karşı
            if start_node_id is not None:
                start_nodes = [start_node_id]
            else:
                start_nodes = find_candidate_nodes(conn, start_lat, start_lon, mode=mode, limit=5)

            if end_node_id is not None:
                end_nodes = [end_node_id]
            else:
                end_nodes = find_candidate_nodes(conn, end_lat, end_lon, mode=mode, limit=5)

            via_nodes = []
            if via_node_id is not None:
                via_nodes = [via_node_id]
            elif via_lat is not None and via_lon is not None:
                via_nodes = find_candidate_nodes(conn, via_lat, via_lon, mode=mode, limit=5)

            if not start_nodes or not end_nodes:
                error_message = "Başlangıç veya bitiş için en yakın düğüm bulunamadı."
            else:
                all_wkts = []
                found_route = False
                cost_m = 0.0

                if via_nodes:
                    # Start -> Via -> End
                    for s_node, v_node, e_node in product(start_nodes, via_nodes, end_nodes):
                        seg1 = get_route_geom_wkts(conn, s_node, v_node, mode=mode)
                        if not seg1: continue
                        
                        seg2 = get_route_geom_wkts(conn, v_node, e_node, mode=mode)
                        if not seg2: continue
                        
                        all_wkts.extend(seg1)
                        all_wkts.extend(seg2)
                        
                        c1 = get_shortest_path_cost(conn, s_node, v_node, mode=mode)
                        c2 = get_shortest_path_cost(conn, v_node, e_node, mode=mode)
                        cost_m = (c1 or 0.0) + (c2 or 0.0)
                        
                        found_route = True
                        break
                else:
                    # Start -> End
                    for s_node, e_node in product(start_nodes, end_nodes):
                        seg = get_route_geom_wkts(conn, s_node, e_node, mode=mode)
                        if seg:
                            all_wkts.extend(seg)
                            cost_m = get_shortest_path_cost(conn, s_node, e_node, mode=mode)
                            found_route = True
                            break

                if not found_route:
                    error_message = "Rota bulunamadı (Seçilen noktalar arasında uygun yol bağlantısı yok)."
                else:
                    if cost_m is not None:
                        total_distance_km = round(cost_m / 1000.0, 2)
                        avg_speed_kmh = get_avg_speed_kmh(mode=mode, speed_profile=speed_profile)
                        estimated_time_min = int(round((total_distance_km / avg_speed_kmh) * 60.0))

                    all_coords = []
                    for wkt in all_wkts:
                        coords = linestring_wkt_to_latlon_list(wkt)
                        all_coords.extend(coords)
                    steps = compute_turn_steps(all_coords)
                    m = create_offline_map(location=[start_lat, start_lon], zoom_start=12, conn=conn)
                    if mode == "yaya":
                        folium.Marker(
                            [start_lat, start_lon],
                            tooltip=f"Başlangıç - {start_place}",
                            icon=folium.Icon(color="green", icon="male", prefix="fa")
                        ).add_to(m)
                        if via_lat and via_lon:
                            folium.Marker(
                                [via_lat, via_lon],
                                tooltip=f"Ara Nokta - {via_place}",
                                icon=folium.Icon(color="orange", icon="flag", prefix="fa")
                            ).add_to(m)
                        folium.Marker(
                            [end_lat, end_lon],
                            tooltip=f"Bitiş - {end_place}",
                            icon=folium.Icon(color="red", icon="male", prefix="fa")
                        ).add_to(m)
                    else:
                        folium.Marker(
                            [start_lat, start_lon],
                            tooltip=f"Başlangıç - {start_place}",
                            icon=folium.Icon(color="green", icon="car", prefix="fa")
                        ).add_to(m)
                        if via_lat and via_lon:
                            folium.Marker(
                                [via_lat, via_lon],
                                tooltip=f"Ara Nokta - {via_place}",
                                icon=folium.Icon(color="orange", icon="flag", prefix="fa")
                            ).add_to(m)
                        folium.Marker(
                            [end_lat, end_lon],
                            tooltip=f"Bitiş - {end_place}",
                            icon=folium.Icon(color="red", icon="car", prefix="fa")
                        ).add_to(m)
                    if all_coords:
                        line_color = "green" if mode == "yaya" else "blue"
                        dash_array = "5, 10" if mode == "yaya" else None
                        folium.PolyLine(all_coords, tooltip="Navigasyon Rotası", color=line_color, weight=5, dash_array=dash_array).add_to(m)
                        min_lat = min(c[0] for c in all_coords)
                        min_lon = min(c[1] for c in all_coords)
                        max_lat = max(c[0] for c in all_coords)
                        max_lon = max(c[1] for c in all_coords)
                        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
                        

                    inject_map_click_js(m)
                    navigation_map_url = save_map_html(
                        m,
                        "navigation_map.html",
                        "show_navigation_map",
                    )

        except Exception as e:
            error_message = f"Navigasyon rotası hesaplanırken hata oluştu: {e}"
        finally:
            close_conn(conn)

    else:
        try:
            start_q = request.args.get("start", "").strip()
            end_q = request.args.get("end", "").strip()
            via_q = request.args.get("via", "").strip()
            mode = request.args.get("mode", "araba").strip()
            speed_profile = request.args.get("profile", "normal").strip()

            if start_q and end_q:
                start_geo = geocode_place(start_q)
                end_geo = geocode_place(end_q)
                via_geo = None
                if via_q:
                    via_geo = geocode_place(via_q)

                if start_geo and end_geo:
                    start_lat, start_lon = start_geo
                    end_lat, end_lon = end_geo
                    via_lat, via_lon = (via_geo if via_geo else (None, None))

                    # Aday node'ları bul (en yakın 5 node)
                    start_nodes = find_candidate_nodes(conn, start_lat, start_lon, mode=mode, limit=5)
                    end_nodes = find_candidate_nodes(conn, end_lat, end_lon, mode=mode, limit=5)
                    via_nodes = []
                    if via_lat is not None and via_lon is not None:
                        via_nodes = find_candidate_nodes(conn, via_lat, via_lon, mode=mode, limit=5)

                    if start_nodes and end_nodes:
                        all_wkts = []
                        found_route = False
                        cost_m = 0.0

                        if via_nodes:
                            for s_node, v_node, e_node in product(start_nodes, via_nodes, end_nodes):
                                seg1 = get_route_geom_wkts(conn, s_node, v_node, mode=mode)
                                if not seg1: continue
                                
                                seg2 = get_route_geom_wkts(conn, v_node, e_node, mode=mode)
                                if not seg2: continue
                                
                                all_wkts.extend(seg1)
                                all_wkts.extend(seg2)
                                
                                c1 = get_shortest_path_cost(conn, s_node, v_node, mode=mode)
                                c2 = get_shortest_path_cost(conn, v_node, e_node, mode=mode)
                                cost_m = (c1 or 0.0) + (c2 or 0.0)
                                found_route = True
                                break
                        else:
                            for s_node, e_node in product(start_nodes, end_nodes):
                                seg = get_route_geom_wkts(conn, s_node, e_node, mode=mode)
                                if seg:
                                    all_wkts.extend(seg)
                                    cost_m = get_shortest_path_cost(conn, s_node, e_node, mode=mode)
                                    found_route = True
                                    break

                        if found_route and cost_m is not None:
                            total_distance_km = round(cost_m / 1000.0, 2)
                            avg_speed_kmh = get_avg_speed_kmh(mode=mode, speed_profile=speed_profile)
                            estimated_time_min = int(round((total_distance_km / avg_speed_kmh) * 60.0))

                            all_coords = []
                            for wkt in all_wkts:
                                coords = linestring_wkt_to_latlon_list(wkt)
                                all_coords.extend(coords)
                            steps = compute_turn_steps(all_coords)
                        m = create_offline_map(location=[start_lat, start_lon], zoom_start=12, conn=conn)
                        if mode == "yaya":
                            folium.Marker([start_lat, start_lon], tooltip=f"Başlangıç - {start_q}", icon=folium.Icon(color="green", icon="male", prefix="fa")).add_to(m)
                            if via_lat and via_lon:
                                folium.Marker([via_lat, via_lon], tooltip=f"Ara Nokta - {via_q}", icon=folium.Icon(color="orange", icon="flag", prefix="fa")).add_to(m)
                            folium.Marker([end_lat, end_lon], tooltip=f"Bitiş - {end_q}", icon=folium.Icon(color="red", icon="male", prefix="fa")).add_to(m)
                        else:
                            folium.Marker([start_lat, start_lon], tooltip=f"Başlangıç - {start_q}", icon=folium.Icon(color="green", icon="car", prefix="fa")).add_to(m)
                            if via_lat and via_lon:
                                folium.Marker([via_lat, via_lon], tooltip=f"Ara Nokta - {via_q}", icon=folium.Icon(color="orange", icon="flag", prefix="fa")).add_to(m)
                            folium.Marker([end_lat, end_lon], tooltip=f"Bitiş - {end_q}", icon=folium.Icon(color="red", icon="car", prefix="fa")).add_to(m)

                        if all_coords:
                            line_color = "green" if mode == "yaya" else "blue"
                            dash_array = "5, 10" if mode == "yaya" else None
                            folium.PolyLine(all_coords, tooltip="Navigasyon Rotası", color=line_color, weight=5, dash_array=dash_array).add_to(m)
                            min_lat = min(c[0] for c in all_coords)
                            min_lon = min(c[1] for c in all_coords)
                            max_lat = max(c[0] for c in all_coords)
                            max_lon = max(c[1] for c in all_coords)
                            m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

                        inject_map_click_js(m)
                        navigation_map_url = save_map_html(
                            m,
                            "navigation_map.html",
                            "show_navigation_map",
                        )
                else:
                    error_message = "Adresler çözümlenemedi."
        except Exception as e:
            error_message = f"GET parametreleriyle rota oluşturulamadı: {e}"
        finally:
            close_conn(conn)

    return render_template(
        "navigation.html",
        db_ok=db_ok,
        db_message=db_message,
        navigation_map_url=navigation_map_url,
        error_message=error_message,
        total_distance_km=total_distance_km,
        estimated_time_min=estimated_time_min,
        mode=mode,
        steps=locals().get("steps", [])
    )


@app.route("/navigation_map")
def show_navigation_map():
    try:
        map_path = os.path.join(app.root_path, "templates", "navigation_map.html")
        with open(map_path, "r", encoding="utf-8") as f:
            html = f.read()
        resp = make_response(html)
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        return resp
    except Exception:
        return render_template("navigation_map.html")

# ======================================================
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Timer(1, open_browser).start()

    app.run(debug=True)
