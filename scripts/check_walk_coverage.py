from sqlalchemy import create_engine, text

# DB Connection
engine = create_engine('postgresql://postgres:123456Qq@localhost:5432/istanbul_gis')

def check_coverage():
    with engine.connect() as conn:
        print("--- nodes_walk Extent ---")
        extent = conn.execute(text("""
            SELECT ST_XMin(ext), ST_YMin(ext), ST_XMax(ext), ST_YMax(ext)
            FROM (SELECT ST_Extent(geometry) as ext FROM nodes_walk) as t
        """)).fetchone()
        print(f"Extent: {extent}")
        
        # Kartal and Maltepe approximate coords (Anadolu)
        kartal = (29.1897, 40.8887)
        maltepe = (29.1309, 40.9248)
        
        # Beşiktaş and Taksim approximate coords (Avrupa)
        besiktas = (29.002, 41.042)
        taksim = (28.986, 41.037)

        print(f"\n--- Checking Kartal {kartal} ---")
        nearest_kartal = conn.execute(text(f"""
            SELECT id, ST_AsText(geometry), ST_Distance(geometry, ST_SetSRID(ST_MakePoint({kartal[0]}, {kartal[1]}), 4326))
            FROM nodes_walk
            ORDER BY geometry <-> ST_SetSRID(ST_MakePoint({kartal[0]}, {kartal[1]}), 4326)
            LIMIT 1
        """)).fetchone()
        print(f"Nearest Node: {nearest_kartal}")
        
        print(f"\n--- Checking Maltepe {maltepe} ---")
        nearest_maltepe = conn.execute(text(f"""
            SELECT id, ST_AsText(geometry), ST_Distance(geometry, ST_SetSRID(ST_MakePoint({maltepe[0]}, {maltepe[1]}), 4326))
            FROM nodes_walk
            ORDER BY geometry <-> ST_SetSRID(ST_MakePoint({maltepe[0]}, {maltepe[1]}), 4326)
            LIMIT 1
        """)).fetchone()
        print(f"Nearest Node: {nearest_maltepe}")
        
        if nearest_kartal and nearest_maltepe:
            start_node = nearest_kartal[0]
            end_node = nearest_maltepe[0]
            print(f"\n--- Testing Route from {start_node} to {end_node} (Anadolu) ---")
            
            # Using pgr_dijkstra with small int IDs
            query = text(f"""
                SELECT count(*), sum(cost)
                FROM pgr_dijkstra(
                    'SELECT id, source, target, cost, reverse_cost FROM edges_walk',
                    {start_node}, {end_node}, true
                )
            """)
            try:
                res = conn.execute(query).fetchone()
                print(f"Path result (count, cost): {res}")
            except Exception as e:
                print(f"Routing failed: {e}")

        # Check Avrupa
        print(f"\n--- Checking Besiktas {besiktas} ---")
        nearest_besiktas = conn.execute(text(f"""
            SELECT id, ST_AsText(geometry), ST_Distance(geometry, ST_SetSRID(ST_MakePoint({besiktas[0]}, {besiktas[1]}), 4326))
            FROM nodes_walk
            ORDER BY geometry <-> ST_SetSRID(ST_MakePoint({besiktas[0]}, {besiktas[1]}), 4326)
            LIMIT 1
        """)).fetchone()
        print(f"Nearest Node: {nearest_besiktas}")

        print(f"\n--- Checking Taksim {taksim} ---")
        nearest_taksim = conn.execute(text(f"""
            SELECT id, ST_AsText(geometry), ST_Distance(geometry, ST_SetSRID(ST_MakePoint({taksim[0]}, {taksim[1]}), 4326))
            FROM nodes_walk
            ORDER BY geometry <-> ST_SetSRID(ST_MakePoint({taksim[0]}, {taksim[1]}), 4326)
            LIMIT 1
        """)).fetchone()
        print(f"Nearest Node: {nearest_taksim}")

        if nearest_besiktas and nearest_taksim:
            start_node = nearest_besiktas[0]
            end_node = nearest_taksim[0]
            print(f"\n--- Testing Route from {start_node} to {end_node} (Avrupa) ---")
            
            # Using pgr_dijkstra with small int IDs
            query = text(f"""
                SELECT count(*), sum(cost)
                FROM pgr_dijkstra(
                    'SELECT id, source, target, cost, reverse_cost FROM edges_walk',
                    {start_node}, {end_node}, true
                )
            """)
            try:
                res = conn.execute(query).fetchone()
                print(f"Path result (count, cost): {res}")
            except Exception as e:
                print(f"Routing failed: {e}")

if __name__ == "__main__":
    check_coverage()
