import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(places)")
for row in cursor.fetchall():
    print(row)
conn.close()