import json
import os

OUTPUT_DIR = r"c:\Users\PC\Desktop\PROJECT-YTU\istanbul_ulasim\static\geojson"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_polygon_feature(name, coordinates):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": name},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                }
            }
        ]
    }

def create_multipolygon_feature(name, coordinates_list):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": name},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": coordinates_list
                }
            }
        ]
    }

# --- 1. ADALAR (MultiPolygon) ---
# Koordinatlar yaklaşık değerlerdir.
adalar_coords = [
    # Büyükada
    [[
        [29.110, 40.850], [29.135, 40.855], [29.140, 40.875], 
        [29.120, 40.885], [29.105, 40.870], [29.110, 40.850]
    ]],
    # Heybeliada
    [[
        [29.080, 40.870], [29.105, 40.875], [29.100, 40.885], 
        [29.075, 40.880], [29.080, 40.870]
    ]],
    # Burgazada
    [[
        [29.055, 40.880], [29.075, 40.885], [29.070, 40.895], 
        [29.050, 40.890], [29.055, 40.880]
    ]],
    # Kınalıada
    [[
        [29.040, 40.900], [29.060, 40.905], [29.055, 40.915], 
        [29.035, 40.910], [29.040, 40.900]
    ]]
]

# --- 2. ANADOLU YAKASI GÜNEY (Kartal, Pendik, Tuzla) ---

# Kartal: Sahilden Aydos'a, Maltepe'den Pendik'e
kartal_coords = [
    [29.150, 40.900], # GB (Sahil-Maltepe sınırı)
    [29.230, 40.880], # GD (Sahil-Pendik sınırı)
    [29.240, 40.940], # KD (Aydos-Pendik)
    [29.160, 40.960], # KB (Aydos-Maltepe)
    [29.150, 40.900]  # Kapanış
]

# Pendik: Kartal'dan Tuzla'ya, Kuzeyde Sabiha Gökçen ve ötesi
pendik_coords = [
    [29.230, 40.870], # GB (Sahil-Kartal)
    [29.300, 40.830], # GD (Sahil-Tuzla)
    [29.380, 40.950], # KD (Kurnaköy civarı)
    [29.320, 41.000], # Kuzey ucu
    [29.240, 40.940], # KB (Kartal sınırı)
    [29.230, 40.870]
]

# Tuzla: Pendik'ten il sınırına, Aydıntepe ve Güzelyalı dahil (Daha Geniş Batı Sınırı)
tuzla_coords = [
    [29.255, 40.848], # Güzelyalı Sahil (Pendik Sınırı - Daha batı)
    [29.255, 40.865], # Güzelyalı/Esenyalı Sınırı (Kuzeye doğru)
    [29.265, 40.875], # Aydıntepe Kuzey / E-5 Üstü
    [29.290, 40.885], # Aydıntepe - Orhanlı geçişi
    [29.310, 40.890], # Orhanlı Batı (Sanayi bölgeleri)
    [29.340, 40.920], # Tepeören
    [29.390, 40.955], # Akfırat / Formula 1 Pisti Kuzeyi
    [29.420, 40.940], # Akfırat Doğu
    [29.435, 40.860], # Şifa/Mimar Sinan (Çayırova Sınırı)
    [29.400, 40.810], # Tuzla - Darıca Sahil Sınırı
    [29.295, 40.800], # Tuzla Burnu (Güney Ucu)
    [29.280, 40.820], # İTÜ Denizcilik Fakültesi civarı
    [29.255, 40.848]  # Başlangıca dönüş
]

# --- 3. AVRUPA YAKASI BÜYÜK İLÇELER (Arnavutköy, Çatalca, Silivri) ---

# Arnavutköy: Çok geniş, kuzeyde Karadeniz, güneyde Sazlıdere
arnavutkoy_coords = [
    [28.600, 41.050], # GB (Hadımköy)
    [28.900, 41.100], # GD (Göktürk sınırı)
    [28.850, 41.300], # KD (Karadeniz)
    [28.550, 41.320], # KB (Karadeniz-Çatalca sınırı)
    [28.600, 41.050]
]

# Çatalca: En batı ve en büyük, Karadeniz'den Marmara'ya (kısmen)
catalca_coords = [
    [28.100, 41.050], # GB (Silivri sınırı)
    [28.550, 41.050], # GD (Büyükçekmece/Arnavutköy)
    [28.550, 41.350], # KD (Karadeniz)
    [28.050, 41.400], # KB (Karadeniz-Tekirdağ)
    [28.100, 41.050]
]

# Silivri: Marmara kıyısı
silivri_coords = [
    [27.900, 41.050], # GB (Gümüşyaka)
    [28.350, 41.030], # GD (Büyükçekmece sınırı)
    [28.350, 41.250], # KD (Çatalca sınırı)
    [28.000, 41.300], # KB (Çerkezköy sınırı)
    [27.900, 41.050]
]

# --- 4. DİĞER EKSİK/HATALI İLÇELER ---

# Beykoz: Boğaz ve Karadeniz
beykoz_coords = [
    [29.050, 41.080], # GB (Anadolu Hisarı)
    [29.250, 41.100], # GD (Çekmeköy/Şile)
    [29.300, 41.200], # KD (Karadeniz-Riva)
    [29.100, 41.220], # KB (Karadeniz-Boğaz çıkışı)
    [29.050, 41.080]
]

# Şile: Karadeniz kıyısı, en doğu
sile_coords = [
    [29.400, 41.050], # GB (Ömerli)
    [29.950, 41.000], # GD (Ağva doğusu)
    [30.000, 41.150], # KD (Karadeniz doğu)
    [29.400, 41.200], # KB (Karadeniz batı)
    [29.400, 41.050]
]

# Beylikdüzü: Küçük, E-5 güneyi
beylikduzu_coords = [
    [28.600, 40.950], # GB (Sahil)
    [28.700, 40.970], # GD (Ambarlı)
    [28.680, 41.010], # KD (E-5)
    [28.580, 41.020], # KB (Büyükçekmece sınırı)
    [28.600, 40.950]
]

# Büyükçekmece: Göl çevresi
buyukcekmece_coords = [
    [28.450, 41.000], # GB (Mimaroba)
    [28.600, 40.980], # GD (Beylikdüzü)
    [28.600, 41.100], # KD (Hadımköy)
    [28.400, 41.080], # KB (Çatalca)
    [28.450, 41.000]
]

# Küçükçekmece: Göl doğusu
kucukcekmece_coords = [
    [28.700, 40.970], # GB (Göl ağzı)
    [28.800, 40.970], # GD (Havalimanı yakını)
    [28.820, 41.050], # KD (Halkalı)
    [28.750, 41.060], # KB (Göl kuzeyi)
    [28.700, 40.970]
]

# Çekmeköy: Ormanlık
cekmekoy_coords = [
    [29.150, 41.020], # GB (Ümraniye)
    [29.350, 41.020], # GD (Ömerli)
    [29.350, 41.100], # KD (Beykoz sınırı)
    [29.200, 41.120], # KB (Beykoz sınırı)
    [29.150, 41.020]
]

# Eyüpsultan: Haliç'ten Karadeniz'e
eyupsultan_coords = [
    [28.920, 41.030], # GB (Haliç)
    [28.950, 41.030], # GD (Haliç)
    [28.950, 41.280], # KD (Karadeniz - Kemerburgaz üstü)
    [28.850, 41.280], # KB (Karadeniz - Arnavutköy sınırı)
    [28.920, 41.030]
]

# Üsküdar: Çok daha detaylı sınır çizimi (Boğaz hattı, komşu ilçe sınırları ve mahalleler)
# GÜNCELLEME 2: Sahil şeridi (özellikle Paşalimanı, Kuzguncuk ve Beylerbeyi) denize doğru daha da genişletildi.
uskudar_coords = [
    # --- COASTLINE (Kuzeyden Güneye - Denize Doğru Maksimum Genişletilmiş) ---
    [29.066, 41.077], # Küçüksu Deresi Ağzı (Kuzey Ucu - Beykoz Sınırı)
    [29.057, 41.075], # Kandilli Kuzey Burnu (Deniz tarafı)
    [29.054, 41.072], # Kandilli İskelesi (Deniz tarafı - Geniş)
    [29.052, 41.068], # Vaniköy Kuzeyi (Deniz tarafı)
    [29.049, 41.065], # Vaniköy İskelesi (Deniz tarafı - Geniş)
    [29.047, 41.060], # Kuleli Askeri Lisesi Önü (Deniz tarafı)
    [29.045, 41.055], # Çengelköy Kuzeyi (Deniz tarafı)
    [29.047, 41.050], # Çengelköy İskelesi (Koy içi - Çok Geniş)
    [29.042, 41.045], # Beylerbeyi Kuzeyi (Deniz tarafı)
    [29.039, 41.042], # Beylerbeyi Sarayı (Deniz tarafı - Geniş)
    [29.034, 41.038], # Beylerbeyi İskelesi (Deniz tarafı)
    [29.031, 41.035], # 15 Temmuz Şehitler Köprüsü Ayağı (Anadolu - Deniz tarafı)
    [29.028, 41.032], # Kuzguncuk Kuzeyi (Deniz tarafı)
    [29.024, 41.030], # Kuzguncuk İskelesi (Deniz tarafı - Çok Geniş)
    [29.020, 41.028], # Paşalimanı (Deniz tarafı - Çok Geniş - Park Alanı)
    [29.015, 41.027], # Fethipaşa Korusu Sahili (Deniz tarafı - Çok Geniş)
    [29.010, 41.027], # Üsküdar Meydan / İskele (Marmaray - Deniz tarafı - Maksimum)
    [29.008, 41.025], # Mihrimah Sultan Camii Önü (Deniz tarafı)
    [29.005, 41.022], # Kız Kulesi Karşısı (Salacak - Deniz tarafı)
    [29.004, 41.018], # Salacak Sahil Yolu Güneyi (Deniz tarafı)
    [29.005, 41.012], # Harem Kuzeyi (Deniz tarafı)
    [29.009, 41.008], # Harem Otogarı (Kıyı Hattı Bitişi - Deniz tarafı)
    
    # --- GÜNEY SINIRI (Kadıköy/Ataşehir ile) ---
    [29.020, 41.005], # Selimiye Kışlası Arkası
    [29.025, 41.003], # Haydarpaşa Numune Arkası
    [29.035, 41.002], # Koşuyolu / E5 Bağlantısı
    [29.045, 41.000], # Validebağ Korusu Güneyi
    [29.055, 40.998], # Acıbadem / Altunizade Sınırı
    [29.065, 40.997], # Küçük Çamlıca Güney Etekleri
    [29.075, 40.996], # Fetih Mahallesi Güneyi (E-5 Kenarı)
    
    # --- DOĞU SINIRI (Ümraniye ile) ---
    [29.085, 41.005], # Libadiye Caddesi Girişi
    [29.090, 41.015], # Bulgurlu Mahallesi
    [29.095, 41.025], # Büyük Çamlıca Tepesi Doğusu
    [29.098, 41.035], # Ferah Mahallesi
    [29.098, 41.045], # Bosna Bulvarı (Nato Yolu)
    [29.095, 41.055], # Yavuztürk Mahallesi
    [29.090, 41.060], # Bahçelievler Mahallesi
    
    # --- KUZEY SINIRI (Beykoz ile) ---
    [29.085, 41.065], # Hekimbaşı Güneyi
    [29.080, 41.070], # Kandilli Rasathanesi Arkası
    [29.075, 41.073], # Sevda Tepesi
    [29.070, 41.075], # Küçüksu İç Kesim
    [29.066, 41.077]  # Başlangıca Dönüş (Küçüksu Ağzı)
]

# Beyoğlu: Haliç ve Boğaz kıyısı, Şişli/Kağıthane sınırı
beyoglu_coords = [
    # Haliç Kıyısı (Güneybatı - Güneydoğu)
    [28.945, 41.045], # Haliç Köprüsü altı (Halıcıoğlu)
    [28.950, 41.040], # Hasköy Sahil
    [28.960, 41.035], # Rahmi Koç Müzesi önü
    [28.968, 41.030], # Kasımpaşa İskelesi
    [28.972, 41.025], # Azapkapı (Haliç Metro Köprüsü)
    [28.975, 41.022], # Karaköy İskelesi (Galata Köprüsü ayağı)
    
    # Boğaz Kıyısı (Doğu)
    [28.980, 41.025], # İstanbul Modern / Galataport
    [28.985, 41.028], # Tophane
    [28.990, 41.030], # Fındıklı
    [28.994, 41.033], # Kabataş İskelesi
    [28.995, 41.035], # Dolmabahçe Camii (Beşiktaş sınırı başlangıcı)
    
    # Kuzey Sınırı (Şişli/Kağıthane ile)
    [28.990, 41.038], # Gümüşsuyu / Taksim doğusu
    [28.985, 41.040], # Taksim Meydanı kuzeyi (Divan Oteli)
    [28.980, 41.042], # Harbiye / TRT Binası arkası
    [28.975, 41.045], # Dolapdere
    [28.970, 41.048], # Piyalepaşa Bulvarı
    [28.965, 41.052], # Okmeydanı sapağı (Şişli sınırı bitişi)
    [28.960, 41.055], # Örnektepe / Kağıthane sınırı
    [28.955, 41.050], # Sütlüce (Miniatürk karşısı)
    [28.945, 41.045]  # Başlangıca dönüş
]

# --- DOSYALARI OLUŞTUR ---

districts_data = {
    "adalar": (create_multipolygon_feature, adalar_coords),
    "kartal": (create_polygon_feature, kartal_coords),
    "pendik": (create_polygon_feature, pendik_coords),
    "tuzla": (create_polygon_feature, tuzla_coords),
    "arnavutkoy": (create_polygon_feature, arnavutkoy_coords),
    "catalca": (create_polygon_feature, catalca_coords),
    "silivri": (create_polygon_feature, silivri_coords),
    "beykoz": (create_polygon_feature, beykoz_coords),
    "sile": (create_polygon_feature, sile_coords),
    "beylikduzu": (create_polygon_feature, beylikduzu_coords),
    "buyukcekmece": (create_polygon_feature, buyukcekmece_coords),
    "kucukcekmece": (create_polygon_feature, kucukcekmece_coords),
    "cekmekoy": (create_polygon_feature, cekmekoy_coords),
    "eyupsultan": (create_polygon_feature, eyupsultan_coords),
    "uskudar": (create_polygon_feature, uskudar_coords),
    "beyoglu": (create_polygon_feature, beyoglu_coords)
}

print("Updating GeoJSON files with detailed polygons...")

for name, (func, coords) in districts_data.items():
    file_path = os.path.join(OUTPUT_DIR, f"{name}.json")
    geojson_content = func(name.capitalize(), coords)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(geojson_content, f, indent=2)
    print(f"Updated {name}.json")

print("All specified districts updated.")
