import osmnx as ox
import geopandas as gpd
from sqlalchemy import create_engine

# 1) İstanbul yol ağını indir (araç yolları)
print("İstanbul yol ağı indiriliyor, biraz sürebilir...")
G = ox.graph_from_place("Istanbul, Turkey", network_type="drive")
print("Yol ağı indirildi.")

# 2) Grafı node ve edge GeoDataFrame'lere çevir
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
print("Graf GeoDataFrame'lere dönüştürüldü.")

# ÖNEMLİ: u ve v, index'teydi, kolona indiriyoruz
edges_gdf = edges_gdf.reset_index()

print("edges kolonları:", edges_gdf.columns)

# 3) edges için pgRouting uyumlu kolonları hazırlayalım
# geometry kolon adını DEĞİŞTİRMİYORUZ (PostGIS tarafında 'geometry' kalacak)
edges = edges_gdf[['u', 'v', 'length', 'geometry']].copy()
edges['id'] = edges.index + 1  # 1'den başlayan id

edges.rename(columns={
    'u': 'source',
    'v': 'target',
    'length': 'cost'
}, inplace=True)

edges['reverse_cost'] = edges['cost']

# Kolon sırasını düzenleyelim
edges = edges[['id', 'source', 'target', 'cost', 'reverse_cost', 'geometry']]

# 4) nodes için id ve geometry kolonlarını hazırlayalım
nodes = nodes_gdf[['geometry']].copy()
nodes['id'] = nodes.index
nodes = nodes[['id', 'geometry']]

print("Nodes ve edges tabloları hazırlandı.")

# 5) PostGIS'e bağlanmak için bağlantı dizesi
DB_NAME = "istanbul_gis"   # veritabanı adın
DB_USER = "postgres"       # kullanıcı adın
DB_PASSWORD = "123456Qq"   # senin şifren
DB_HOST = "localhost"
DB_PORT = "5432"

conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(conn_str)

# 6) GeoDataFrame'leri PostGIS'e yaz
print("nodes tablosu PostGIS'e yazılıyor...")
nodes.to_postgis("nodes", engine, if_exists="replace", index=False)

print("edges tablosu PostGIS'e yazılıyor...")
edges.to_postgis("edges", engine, if_exists="replace", index=False)

print("İşlem tamamlandı! nodes ve edges tabloları PostGIS'te oluşturuldu.")
