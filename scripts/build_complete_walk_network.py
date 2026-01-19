import osmnx as ox
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, text
import psycopg2
import sys
import time

# Veritabanı Ayarları
DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASSWORD = "123456Qq"
DB_HOST = "localhost"
DB_PORT = "5432"

CONN_STR = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# OSMnx Ayarları (Yeni versiyon uyumluluğu)
if hasattr(ox, 'settings'):
    ox.settings.use_cache = True
    ox.settings.log_console = False
else:
    ox.config(use_cache=True, log_console=False)

def build_complete_walk_network():
    print("=== İstanbul TAM Kapsamlı Yaya Ağı Oluşturma Aracı (Iterative) ===")
    print("39 İlçe tek tek indirilip birleştirilecek.")
    
    try:
        places = [
            # Anadolu Yakası
            "Adalar, Istanbul, Turkey", 
            "Ataşehir, Istanbul, Turkey", 
            "Beykoz, Istanbul, Turkey", 
            "Çekmeköy, Istanbul, Turkey", 
            "Kartal, Istanbul, Turkey", 
            "Kadikoy, Istanbul, Turkey", 
            "Maltepe, Istanbul, Turkey", 
            "Pendik, Istanbul, Turkey", 
            "Sancaktepe, Istanbul, Turkey", 
            "Sultanbeyli, Istanbul, Turkey", 
            "Şile, Istanbul, Turkey", 
            "Tuzla, Istanbul, Turkey", 
            "Ümraniye, Istanbul, Turkey", 
            "Üsküdar, Istanbul, Turkey",
            
            # Avrupa Yakası
            "Arnavutköy, Istanbul, Turkey", 
            "Avcılar, Istanbul, Turkey", 
            "Bağcılar, Istanbul, Turkey", 
            "Bahçelievler, Istanbul, Turkey", 
            "Bakırköy, Istanbul, Turkey", 
            "Başakşehir, Istanbul, Turkey", 
            "Bayrampaşa, Istanbul, Turkey", 
            "Beşiktaş, Istanbul, Turkey", 
            "Beylikdüzü, Istanbul, Turkey", 
            "Beyoğlu, Istanbul, Turkey", 
            "Büyükçekmece, Istanbul, Turkey", 
            "Çatalca, Istanbul, Turkey", 
            "Esenler, Istanbul, Turkey", 
            "Esenyurt, Istanbul, Turkey", 
            "Eyüpsultan, Istanbul, Turkey", 
            "Fatih, Istanbul, Turkey", 
            "Gaziosmanpaşa, Istanbul, Turkey", 
            "Güngören, Istanbul, Turkey", 
            "Kağıthane, Istanbul, Turkey", 
            "Küçükçekmece, Istanbul, Turkey", 
            "Sarıyer, Istanbul, Turkey", 
            "Silivri, Istanbul, Turkey", 
            "Sultangazi, Istanbul, Turkey", 
            "Şişli, Istanbul, Turkey", 
            "Zeytinburnu, Istanbul, Turkey"
        ]
        
        all_nodes_gdfs = []
        all_edges_gdfs = []
        
        print(f"\n1. {len(places)} ilçe taranıyor...")
        
        for i, place in enumerate(places, 1):
            print(f"   [{i}/{len(places)}] İndiriliyor: {place} ... ", end="", flush=True)
            try:
                # 1. Alanın sınırlarını al ve genişlet (Buffer)
                gdf = ox.geocode_to_gdf(place)
                # Projeksiyon yap (metre cinsinden buffer için) - Istanbul UTM Zone 35N
                gdf_utm = gdf.to_crs(epsg=32635)
                # 200 metre buffer ekle (sınır geçişleri için)
                gdf_utm['geometry'] = gdf_utm.geometry.buffer(200)
                # Tekrar Lat/Lon'a çevir
                gdf_buffered = gdf_utm.to_crs(epsg=4326)
                polygon = gdf_buffered.geometry[0]

                # 2. Genişletilmiş alandan grafı indir
                # simplify=True önemli, veri boyutunu düşürür
                G = ox.graph_from_polygon(polygon, network_type='walk', simplify=True)
                
                nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
                
                # Sütun uyumluluğu için reset_index
                nodes_gdf = nodes_gdf.reset_index()
                edges_gdf = edges_gdf.reset_index()
                
                all_nodes_gdfs.append(nodes_gdf)
                all_edges_gdfs.append(edges_gdf)
                print(f"OK (Nodes: {len(nodes_gdf)}, Edges: {len(edges_gdf)})")
                
            except Exception as e:
                print(f"HATA! -> {e}")
                # Hata olsa bile devam et (diğer ilçeler için)

        print("\n2. Veriler Birleştiriliyor...")
        if not all_nodes_gdfs:
            print("Hiç veri indirilemedi!")
            return

        # --- NODES MERGE ---
        full_nodes = pd.concat(all_nodes_gdfs, ignore_index=True)
        # OSM ID (veya index) kolonunu bul
        if 'osmid' not in full_nodes.columns:
            if 'index' in full_nodes.columns:
                full_nodes.rename(columns={'index': 'osmid'}, inplace=True)
            elif 'id' in full_nodes.columns: # bazen id olarak gelir
                 full_nodes.rename(columns={'id': 'osmid'}, inplace=True)
        
        # Duplicate removal (Aynı node birden fazla ilçede olabilir - sınır komşusu)
        print(f"   Toplam Ham Node: {len(full_nodes)}")
        full_nodes.drop_duplicates(subset=['osmid'], inplace=True)
        print(f"   Tekil Node: {len(full_nodes)}")

        # --- EDGES MERGE ---
        full_edges = pd.concat(all_edges_gdfs, ignore_index=True)
        print(f"   Toplam Ham Edge: {len(full_edges)}")
        # Edges unique check: (u, v, key) or (u, v)
        # OSMnx edges have u, v, key.
        full_edges.drop_duplicates(subset=['u', 'v', 'key'], inplace=True)
        print(f"   Tekil Edge: {len(full_edges)}")

        # 3. ID Remapping
        print("\n3. ID Dönüşümü (BigInt -> Integer) yapılıyor...")
        
        # Yeni sıralı ID
        full_nodes['new_id'] = range(1, len(full_nodes) + 1)
        id_map = pd.Series(full_nodes.new_id.values, index=full_nodes.osmid).to_dict()
        
        full_edges['source_new'] = full_edges['u'].map(id_map)
        full_edges['target_new'] = full_edges['v'].map(id_map)
        
        # Maplenemeyenleri temizle
        full_edges.dropna(subset=['source_new', 'target_new'], inplace=True)
        full_edges['source_new'] = full_edges['source_new'].astype(int)
        full_edges['target_new'] = full_edges['target_new'].astype(int)

        # 4. Veritabanına Yazma
        engine = create_engine(CONN_STR)
        
        # --- NODES ---
        print("\n4. 'nodes_walk' tablosu hazırlanıyor...")
        nodes_export = pd.DataFrame()
        nodes_export['id'] = full_nodes['new_id']
        nodes_export['osm_id'] = full_nodes['osmid']
        nodes_export['geometry'] = full_nodes['geometry']
        
        nodes_export_gdf = gpd.GeoDataFrame(nodes_export, geometry='geometry')
        nodes_export_gdf.set_crs(epsg=4326, inplace=True)
        
        print("   PostGIS'e yazılıyor (nodes_walk)...")
        nodes_export_gdf.to_postgis('nodes_walk', engine, if_exists='replace', index=False, chunksize=20000)
        
        with engine.connect() as con:
            con.execute(text("ALTER TABLE nodes_walk ADD PRIMARY KEY (id);"))
            con.execute(text("CREATE INDEX idx_nodes_walk_geom ON nodes_walk USING GIST(geometry);"))
            con.commit()

        # --- EDGES ---
        print("\n5. 'edges_walk' tablosu hazırlanıyor...")
        edges_export = pd.DataFrame()
        edges_export['source'] = full_edges['source_new']
        edges_export['target'] = full_edges['target_new']
        edges_export['cost'] = full_edges['length']
        edges_export['reverse_cost'] = full_edges['length']
        edges_export['geometry'] = full_edges['geometry']
        
        # osm_id sütunu varsa ekle
        if 'osmid' in full_edges.columns:
             # osmid bazen liste olabilir, string'e çevirmek gerekebilir ama postgis list desteklemez.
             # Genelde tek değerdir ama birleştirilmiş yollarda liste olur.
             # Basitleştirmek için ilk elemanı veya string halini alalım.
             edges_export['osm_id'] = full_edges['osmid'].astype(str)
        
        edges_export_gdf = gpd.GeoDataFrame(edges_export, geometry='geometry')
        edges_export_gdf.set_crs(epsg=4326, inplace=True)

        print("   PostGIS'e yazılıyor (edges_walk)...")
        edges_export_gdf.to_postgis('edges_walk', engine, if_exists='replace', index=False, chunksize=20000)

        with engine.connect() as con:
            print("   Indexler oluşturuluyor...")
            con.execute(text("ALTER TABLE edges_walk ADD COLUMN id SERIAL PRIMARY KEY;"))
            con.execute(text("CREATE INDEX idx_edges_walk_source ON edges_walk(source);"))
            con.execute(text("CREATE INDEX idx_edges_walk_target ON edges_walk(target);"))
            con.execute(text("CREATE INDEX idx_edges_walk_geom ON edges_walk USING GIST(geometry);"))
            con.commit()

        print("\n=== İŞLEM BAŞARIYLA TAMAMLANDI! ===")
        print(f"Toplam {len(full_nodes)} düğüm ve {len(full_edges)} yol kaydedildi.")
        
    except Exception as e:
        print(f"\n!!! GENEL HATA: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    build_complete_walk_network()
