import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
c.execute("SELECT id, wilaya, commune, nom, latitude, longitude, place_id FROM facilities WHERE commune = 'Ain Smara'")
rows = c.fetchall()
print(f"Total facilities in Ain Smara: {len(rows)}")
for r in rows:
    print(r)

print("\n--- Checking structures table ---")
c.execute("PRAGMA table_info(structures)")
cols = [col[1] for col in c.fetchall()]
print("structures columns:", cols)

c.execute("SELECT count(*) FROM structures")
print("Total in structures table:", c.fetchone()[0])

c.execute("SELECT nom, commune, wilaya, latitude, longitude FROM structures WHERE commune = 'Ain Smara' LIMIT 10")
for r in c.fetchall():
    print("structure:", r)

conn.close()

