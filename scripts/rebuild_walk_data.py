import osmnx as ox
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, text
import psycopg2

# DB Config
# Not: psycopg2 için connection string ve sqlalchemy için ayrı
DB_CONN_STR = "postgresql://postgres:123456Qq@localhost:5432/istanbul_gis"

def rebuild_walk_data():
    try:
        print("1. Tabloları temizle...")
        conn = psycopg2.connect(
            dbname="istanbul_gis",
            user="postgres",
            password="123456Qq",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        
        # Tabloları düşür
        cur.execute("DROP TABLE IF EXISTS edges_walk CASCADE;")
        cur.execute("DROP TABLE IF EXISTS nodes_walk CASCADE;")
        
        # Tabloları oluştur (Boş olarak, to_postgis dolduracak ama indexleri sonra ekleyebiliriz veya to_postgis oluşturur)
        # to_postgis tabloyu oluşturur, biz sadece mevcutsa düşürdük.
        
        conn.commit()
        conn.close()

        print("2. OSM verisini indir (İstanbul Geneli - 25km radius)...")
        # Ayarlar
        ox.settings.use_cache = True
        ox.settings.log_console = True
        
        # İstanbul Merkez (Tarihi Yarımada / Eminönü)
        center_point = (41.015, 28.979)
        # 25km yarıçap (Avrupa: Sarıyer-Bakırköy, Anadolu: Beykoz-Kartal arası)
        dist = 25000 
        
        G = ox.graph_from_point(center_point, dist=dist, network_type='walk')
        
        print(f"   İndirilen düğüm sayısı: {len(G.nodes)}")
        print(f"   İndirilen kenar sayısı: {len(G.edges)}")

        print("3. GeoDataFrame'e çevir...")
        nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)

        # DB Engine
        engine = create_engine(DB_CONN_STR)

        # 4. Nodes yükle
        print("4. Node verilerini yüklüyor...")
        # Index'i (osmid) 'id' sütununa çevir
        nodes_gdf = nodes_gdf.reset_index()
        nodes_gdf = nodes_gdf[['osmid', 'geometry']]
        nodes_gdf.rename(columns={'osmid': 'osm_id'}, inplace=True)
        
        # Yeni sıralı ID (Integer) oluştur
        nodes_gdf['id'] = range(1, len(nodes_gdf) + 1)
        
        # Mapping sözlüğü: OSM ID -> Yeni ID
        # OSM ID'ler çok büyük (BigInt) olduğu için pgRouting'de sorun çıkarıyor.
        # Bu yüzden 1'den başlayan integer ID'ler kullanacağız.
        osm_to_new_id = pd.Series(nodes_gdf.id.values, index=nodes_gdf.osm_id).to_dict()
        
        print("   Node ID mapping hazırlandı.")
        
        nodes_gdf.to_postgis('nodes_walk', engine, if_exists='replace', index=False, chunksize=5000)
        
        # Primary Key ekle
        with engine.connect() as con:
            con.execute(text("ALTER TABLE nodes_walk ADD PRIMARY KEY (id);"))
            con.execute(text("CREATE INDEX idx_nodes_walk_osmid ON nodes_walk(osm_id);"))
            con.commit()

        # 5. Edges yükle
        print("5. Edge verilerini yüklüyor...")
        edges_gdf = edges_gdf.reset_index()
        
        # Gerekli sütunları seç ve yeniden adlandır
        # osmnx edges: u, v, key, osmid, length, geometry, highway, ...
        # u -> source, v -> target
        
        edges_export = pd.DataFrame()
        
        # OSM ID'lerini (u, v) yeni integer ID'lere çevir
        # Maplenemeyenler (dışarıda kalanlar) NaN olur, onları temizleriz.
        edges_export['source'] = edges_gdf['u'].map(osm_to_new_id)
        edges_export['target'] = edges_gdf['v'].map(osm_to_new_id)
        
        # Kayıp node varsa temizle (olmaması gerekir ama tedbir)
        edges_export.dropna(subset=['source', 'target'], inplace=True)
        
        # Integer'a çevir
        edges_export['source'] = edges_export['source'].astype(int)
        edges_export['target'] = edges_export['target'].astype(int)
        
        edges_export['cost'] = edges_gdf['length']
        edges_export['reverse_cost'] = edges_gdf['length'] # Yaya yolları genelde çift yönlü
        edges_export['geometry'] = edges_gdf['geometry']
        
        # Highway (yol tipi) sütunu varsa ekle, yoksa None
        if 'highway' in edges_gdf.columns:
            # highway kolonu bazen liste (['footway', 'steps']) gelebilir, string'e çevirelim
            edges_export['highway'] = edges_gdf['highway'].astype(str)
        else:
            edges_export['highway'] = None
        
        # GeoDataFrame yap
        edges_export_gdf = gpd.GeoDataFrame(edges_export, geometry='geometry')
        edges_export_gdf.set_crs(epsg=4326, inplace=True)
        
        edges_export_gdf.to_postgis('edges_walk', engine, if_exists='replace', index=False, chunksize=5000)
        
        # ID ve Indexler
        with engine.connect() as con:
            con.execute(text("ALTER TABLE edges_walk ADD COLUMN id SERIAL PRIMARY KEY;"))
            con.execute(text("CREATE INDEX idx_edges_walk_source ON edges_walk(source);"))
            con.execute(text("CREATE INDEX idx_edges_walk_target ON edges_walk(target);"))
            con.execute(text("CREATE INDEX idx_edges_walk_geom ON edges_walk USING GIST(geometry);"))
            con.commit()

        print("İşlem başarıyla tamamlandı.")
        
    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    rebuild_walk_data()
