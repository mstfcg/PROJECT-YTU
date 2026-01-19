import osmnx as ox
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, text
import psycopg2
import os

# Veritabanı Ayarları
DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASSWORD = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

CONN_STR = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def build_full_walk_network():
    print("=== İstanbul Yaya Ağı Oluşturma Aracı ===")
    print("Bu işlem tüm İstanbul için yaya yollarını indirir.")
    print("UYARI: Yaya verisi araç verisinden çok daha büyüktür. Bu işlem zaman alabilir ve yüksek RAM kullanabilir.")
    
    try:
        # 1. Veritabanı bağlantısı ve tablo temizliği
        print("\n1. Eski tablolar temizleniyor (nodes_walk, edges_walk)...")
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS edges_walk CASCADE;")
        cur.execute("DROP TABLE IF EXISTS nodes_walk CASCADE;")
        conn.commit()
        conn.close()
        
        # 2. OSM Verisini İndir
        print("\n2. OSM'den Yaya Ağı İndiriliyor (network_type='walk')...")
        # Bellek sorunu yaşanırsa burayı küçültmek gerekebilir (örn: sadece belirli ilçeler)
        # Şimdilik tüm İstanbul'u deniyoruz.
        place_name = "Istanbul, Turkey"
        
        # graph_from_place bazen çok büyük alanlarda timeout verebilir.
        G = ox.graph_from_place(place_name, network_type='walk')
        
        print(f"   İndirilen düğüm sayısı: {len(G.nodes)}")
        print(f"   İndirilen kenar sayısı: {len(G.edges)}")

        # 3. GeoDataFrame dönüşümü
        print("\n3. Veri GeoDataFrame formatına dönüştürülüyor...")
        nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)

        # 4. Veritabanına Yazma Hazırlığı
        engine = create_engine(CONN_STR)

        # --- NODES ---
        print("\n4. 'nodes_walk' tablosu hazırlanıyor...")
        nodes_gdf = nodes_gdf.reset_index()
        # Sadece ihtiyacımız olan kolonlar
        nodes_export = nodes_gdf[['osmid', 'geometry']].copy()
        nodes_export.rename(columns={'osmid': 'id'}, inplace=True)
        
        print("   PostGIS'e yazılıyor...")
        nodes_export.to_postgis('nodes_walk', engine, if_exists='replace', index=False, chunksize=5000)
        
        # Primary Key
        with engine.connect() as con:
            con.execute(text("ALTER TABLE nodes_walk ADD PRIMARY KEY (id);"))
            con.execute(text("CREATE INDEX idx_nodes_walk_geom ON nodes_walk USING GIST(geometry);"))
            con.commit()

        # --- EDGES ---
        print("\n5. 'edges_walk' tablosu hazırlanıyor...")
        edges_gdf = edges_gdf.reset_index()
        
        edges_export = pd.DataFrame()
        # OSMnx sütun isimleri versiyona göre değişebilir ama genelde u, v, key, length şeklindedir
        edges_export['source'] = edges_gdf['u']
        edges_export['target'] = edges_gdf['v']
        edges_export['cost'] = edges_gdf['length']
        
        # Yaya yollarında ters yön maliyeti genellikle düz yön ile aynıdır (çift yönlü)
        # Eğer 'oneway' sütunu varsa ve True ise dikkate alınabilir ama yayalar için çoğu yol çift yönlüdür.
        # Basitleştirmek için hepsini çift yönlü kabul ediyoruz.
        edges_export['reverse_cost'] = edges_gdf['length'] 
        
        edges_export['geometry'] = edges_gdf['geometry']
        
        edges_export_gdf = gpd.GeoDataFrame(edges_export, geometry='geometry')
        edges_export_gdf.set_crs(epsg=4326, inplace=True)

        print("   PostGIS'e yazılıyor...")
        edges_export_gdf.to_postgis('edges_walk', engine, if_exists='replace', index=False, chunksize=5000)

        # Indexler
        with engine.connect() as con:
            print("   Indexler oluşturuluyor...")
            con.execute(text("ALTER TABLE edges_walk ADD COLUMN id SERIAL PRIMARY KEY;"))
            con.execute(text("CREATE INDEX idx_edges_walk_source ON edges_walk(source);"))
            con.execute(text("CREATE INDEX idx_edges_walk_target ON edges_walk(target);"))
            con.execute(text("CREATE INDEX idx_edges_walk_geom ON edges_walk USING GIST(geometry);"))
            con.commit()

        print("\n=== İşlem Başarıyla Tamamlandı! ===")
        print("Artık 'Yaya' modu seçildiğinde bu yeni veriler kullanılacak.")

    except Exception as e:
        print(f"\n!!! HATA OLUŞTU !!!\n{e}")

if __name__ == "__main__":
    build_full_walk_network()
