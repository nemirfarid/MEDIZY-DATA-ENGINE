import sqlite3

conn_sc = sqlite3.connect('medizy_scraper.db')
c_sc = conn_sc.cursor()
c_sc.execute("PRAGMA table_info(places)")
for c in c_sc.fetchall():
    print(c[1], end=", ")
print()

c_sc.execute("SELECT * FROM places WHERE id = 63539")
print("Place 63539:", c_sc.fetchone())
conn_sc.close()
