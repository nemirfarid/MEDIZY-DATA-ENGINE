import sqlite3

conn = sqlite3.connect('medizy_scraper.db')
c = conn.cursor()
c.execute("PRAGMA table_info(communes)")
print("communes columns:", c.fetchall())
c.execute("PRAGMA table_info(wilayas)")
print("wilayas columns:", c.fetchall())

