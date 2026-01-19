from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:123456Qq@localhost:5432/istanbul_gis')
with engine.connect() as conn:
    res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
    print([r[0] for r in res])
