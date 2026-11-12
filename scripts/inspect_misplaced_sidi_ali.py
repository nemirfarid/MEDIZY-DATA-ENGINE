import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Check facilities assigned to Sidi Ali that are outside the urban boundary of Sidi Ali
# Sidi Ali town center is around (36.095 to 36.115, 0.405 to 0.435)
c.execute("""
    SELECT id, nom, latitude, longitude, commune, wilaya 
    FROM facilities 
    WHERE commune = 'Sidi Ali' AND (latitude < 36.08 OR latitude > 36.13 OR longitude < 0.39 OR longitude > 0.45)
""")
misplaced_sidi_ali = c.fetchall()
print(f"Structures labeled 'Sidi Ali' that are far outside Sidi Ali urban bounds: {len(misplaced_sidi_ali)}")
for r in misplaced_sidi_ali[:20]:
    print("  ", r)

conn.close()

