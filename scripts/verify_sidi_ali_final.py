import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Check facilities in Sidi Ali now
c.execute("SELECT id, nom, categorie, latitude, longitude, commune, source FROM facilities WHERE commune = 'Sidi Ali'")
rows = c.fetchall()
print(f"Total genuine structures in Sidi Ali: {len(rows)}")
for r in rows:
    print("  ", r)

conn.close()

