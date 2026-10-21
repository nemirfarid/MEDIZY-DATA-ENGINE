import sqlite3
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()
c.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = c.fetchall()
print("Tables:", tables)
for t in tables:
    c.execute(f'SELECT COUNT(*) FROM {t[0]}')
    count = c.fetchone()[0]
    print(f"  {t[0]}: {count} rows")
conn.close()