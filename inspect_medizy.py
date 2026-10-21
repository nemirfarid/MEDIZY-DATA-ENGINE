import sqlite3

print("=== Scraper DB: medizy_scraper.db (31MB) ===")
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables: {tables}")

for t in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM [{t}]")
        cnt = cursor.fetchone()[0]
        print(f"  {t}: {cnt} rows")
    except Exception as e:
        print(f"  {t}: ERROR - {e}")

# Check data_sources
print("\n=== data_sources ===")
cursor.execute("SELECT * FROM data_sources")
cols = [d[0] for d in cursor.description]
print(f"Columns: {cols}")
for row in cursor.fetchall():
    print(row)

# Check source_registry
print("\n=== source_registry ===")
try:
    cursor.execute("SELECT * FROM source_registry")
    cols = [d[0] for d in cursor.description]
    print(f"Columns: {cols}")
    for row in cursor.fetchall():
        print(row)
except Exception as e:
    print(f"ERROR: {e}")

conn.close()
