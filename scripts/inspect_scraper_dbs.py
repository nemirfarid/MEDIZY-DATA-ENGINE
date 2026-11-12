import sqlite3

for db in ['medizy_scraper.db', 'medizy_scraper_national_test.db', 'medizy_scraper_test.db']:
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        print(f"\nDatabase: {db}")
        for t in tables:
            tname = t[0]
            if not tname.startswith('sqlite_'):
                count = c.execute(f"SELECT count(1) FROM {tname}").fetchone()[0]
                print(f"   Table '{tname}': {count} rows")
        conn.close()
    except Exception as e:
        print(db, "error:", e)

