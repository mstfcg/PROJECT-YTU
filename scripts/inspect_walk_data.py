from sqlalchemy import create_engine, text

# DB Connection
engine = create_engine('postgresql://postgres:123456Qq@localhost:5432/istanbul_gis')

def inspect_data():
    with engine.connect() as conn:
        print("--- Row Counts ---")
        rows_nodes = conn.execute(text("SELECT count(*) FROM nodes_walk")).scalar()
        rows_edges = conn.execute(text("SELECT count(*) FROM edges_walk")).scalar()
        print(f"nodes_walk: {rows_nodes}")
        print(f"edges_walk: {rows_edges}")

        print("\n--- nodes_walk Sample (id, osm_id) ---")
        # Assuming 'id' is the PK. Check if 'osm_id' exists or if 'id' IS the osm_id.
        # Let's check columns first
        cols_nodes = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'nodes_walk'")).fetchall()
        print(f"Columns: {cols_nodes}")
        
        # Get sample
        res_nodes = conn.execute(text("SELECT * FROM nodes_walk LIMIT 5")).fetchall()
        print(res_nodes)

        print("\n--- edges_walk Sample (source, target, id) ---")
        cols_edges = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'edges_walk'")).fetchall()
        print(f"Columns: {cols_edges}")

        res_edges = conn.execute(text("SELECT source, target, id FROM edges_walk LIMIT 5")).fetchall()
        print(res_edges)
        
        print("\n--- Check ID Match ---")
        # Check if a source from edges_walk exists in nodes_walk.id
        if rows_edges > 0:
            sample_source = res_edges[0][0]
            print(f"Checking if source {sample_source} exists in nodes_walk.id...")
            match = conn.execute(text(f"SELECT count(*) FROM nodes_walk WHERE id = {sample_source}")).scalar()
            print(f"Match count: {match}")

            # Check max ID values
            max_node_id = conn.execute(text("SELECT max(id) FROM nodes_walk")).scalar()
            max_edge_source = conn.execute(text("SELECT max(source) FROM edges_walk")).scalar()
            print(f"Max node id: {max_node_id}")
            print(f"Max edge source: {max_edge_source}")

if __name__ == "__main__":
    inspect_data()
