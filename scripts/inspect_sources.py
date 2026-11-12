import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT source, count(1) FROM facilities GROUP BY source")
for r in c.fetchall():
    print("Source:", r)

conn.close()

