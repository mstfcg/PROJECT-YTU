import psycopg2
import os

DB_HOST = "localhost"
DB_NAME = "istanbul_gis"
DB_USER = "postgres"
DB_PASSWORD = "123456Qq"
DB_PORT = "5432"

def test_route():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # 1. Koordinatlar (Küçükyalı -> Küçükyalı Metro)
        start_lat, start_lon = 40.9462581, 29.1071691
        end_lat, end_lon = 40.948159, 29.124013

        print(f"Start: {start_lat}, {start_lon}")
        print(f"End: {end_lat}, {end_lon}")

        # 2. En yakın düğümleri bul (yaya)
        def get_nearest_node(lat, lon):
            query = """
                SELECT id, ST_Distance(geometry, ST_SetSRID(ST_Point(%s, %s), 4326)) as dist
                FROM nodes_walk
                ORDER BY geometry <-> ST_SetSRID(ST_Point(%s, %s), 4326)
                LIMIT 1;
            """
            cur.execute(query, (lon, lat, lon, lat))
            return cur.fetchone()

        start_node = get_nearest_node(start_lat, start_lon)
        end_node = get_nearest_node(end_lat, end_lon)

        if not start_node or not end_node:
            print("Düğüm bulunamadı!")
            return

        print(f"Start Node: {start_node[0]} (Dist: {start_node[1]})")
        print(f"End Node: {end_node[0]} (Dist: {end_node[1]})")

        # 3. Rota hesapla (pgr_dijkstra)
        # edges_walk tablosunda cost pozitif olmalı.
        route_query = """
            SELECT * FROM pgr_dijkstra(
                'SELECT id, source, target, cost, reverse_cost FROM edges_walk',
                %s, %s, directed := false
            );
        """
        # Yaya yolları genelde çift yönlüdür, directed:=false deniyorum veya reverse_cost kontrolü.
        # edges_walk yapısını kontrol etmiştik, reverse_cost sütunu vardı.
        
        print("Calculating route (directed=False)...")
        cur.execute(route_query, (start_node[0], end_node[0]))
        rows = cur.fetchall()
        
        if rows:
            print(f"Route found! Steps: {len(rows)}")
            total_cost = sum(r[3] for r in rows) # agg_cost in last row usually, but here checking step costs
            print(f"Total Cost: {total_cost}")
        else:
            print("Route NOT found with directed=False")

            # Alternatif: Yarıçapı artırarak en yakın 5 düğümü dene
            print("\nTrying multiple candidate nodes...")
            # (Burada basitçe 1-1 denedik, başarısızsa veri kopuk olabilir)

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_route()
