import sqlite3

for db_name in ['medizy_scraper.db', 'assets/data/sante_dz_bundled.db']:
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(db_name, c.fetchall())

