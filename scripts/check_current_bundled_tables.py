import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables in assets/data/sante_dz_bundled.db:")
for t in tables:
    cnt = c.execute(f"SELECT count(*) FROM {t[0]}").fetchone()[0]
    print(f"  {t[0]}: {cnt} rows")

c.execute("SELECT * FROM facilities LIMIT 3")
for r in c.fetchall():
    print("Sample facility:", r)

conn.close()

