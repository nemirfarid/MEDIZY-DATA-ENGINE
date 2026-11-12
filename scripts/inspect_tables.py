import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables in bundled DB:", c.fetchall())

c.execute("SELECT source, count(1) FROM facilities GROUP BY source")
print("Facilities sources:", c.fetchall())

# Check how many facilities have place_id
c.execute("SELECT count(1) FROM facilities WHERE place_id IS NOT NULL AND place_id != ''")
print("Facilities with place_id:", c.fetchone()[0])

conn.close()

