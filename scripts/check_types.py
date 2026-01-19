from sqlalchemy import create_engine, text

try:
    engine = create_engine('postgresql://postgres:123456Qq@localhost:5432/istanbul_gis')
    with engine.connect() as conn:
        print('--- edges_walk column types ---')
        res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'edges_walk'"))
        for row in res.fetchall():
            print(row)
            
        print('\n--- Sample source/target values ---')
        res = conn.execute(text("SELECT source, target FROM edges_walk LIMIT 5"))
        for row in res.fetchall():
            print(row)

except Exception as e:
    print(e)
