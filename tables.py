import sqlite3

conn = sqlite3.connect('C:\\SANTE_DZ_SCRAPER\\medizy_scraper.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
for t in tables:
    print(t[0])
conn.close()
