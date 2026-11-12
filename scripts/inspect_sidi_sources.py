import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT source, count(1) FROM facilities WHERE commune = 'Sidi Ali' GROUP BY source")
print("Sidi Ali breakdown by source:", c.fetchall())

conn.close()

