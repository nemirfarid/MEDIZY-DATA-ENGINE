import sqlite3

for db_path in ['medizy_scraper_national_test.db', 'medizy_scraper_synthetic.db', 'medizy_scraper_test.db']:
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        tables = [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"=== {db_path} ===")
        print("  Tables:", tables[:5])
        if 'places' in tables:
            cnt = c.execute("SELECT count(*) FROM places").fetchone()[0]
            print(f"  places count: {cnt}")
        if 'facilities' in tables:
            cnt = c.execute("SELECT count(*) FROM facilities").fetchone()[0]
            print(f"  facilities count: {cnt}")
        conn.close()
    except Exception as e:
        print(f"Error {db_path}:", e)

