from sqlalchemy import create_engine, text

try:
    engine = create_engine('postgresql://postgres:123456Qq@localhost:5432/istanbul_gis')
    with engine.connect() as conn:
        print('--- edges columns ---')
        try:
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'edges'"))
            cols = [r[0] for r in res]
            print(cols)
            if not cols:
                print("Warning: 'edges' table columns not found (list is empty).")
        except Exception as e:
            print(f"Error querying edges: {e}")

        print('\n--- edges_walk columns ---')
        try:
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'edges_walk'"))
            cols = [r[0] for r in res]
            print(cols)
        except Exception as e:
            print(f"Error querying edges_walk: {e}")

except Exception as main_e:
    print(f"Connection failed: {main_e}")
