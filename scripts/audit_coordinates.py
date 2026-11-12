import sqlite3

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()
bad = cur.execute("SELECT count(*) FROM facilities WHERE wilaya = 'Mostaganem' AND latitude < 35.0").fetchone()[0]
good = cur.execute("SELECT count(*) FROM facilities WHERE wilaya = 'Mostaganem' AND latitude >= 35.0").fetchone()[0]
print(f"Mostaganem facilities: {bad} have bad lat (<35.0, e.g. 33.3), and {good} have real lat (>=35.0)")

# Check nationwide: which other wilayas have dummy/bad coordinates?
rows = cur.execute("""
SELECT wilaya_code, wilaya, count(*), min(latitude), max(latitude), min(longitude), max(longitude)
FROM facilities
GROUP BY wilaya_code, wilaya
ORDER BY count(*) DESC
""").fetchall()

print(f"\nTotal wilayas in DB: {len(rows)}")
bad_wilayas = []
for r in rows:
    code, wname, cnt, min_lat, max_lat, min_lon, max_lon = r
    # Algeria bounds roughly lat: [18.9, 37.2], lon: [-8.7, 12.0]
    # Check if a wilaya has all coordinates collapsed at dummy point
    if min_lat == max_lat:
        bad_wilayas.append((code, wname, cnt, min_lat, min_lon))
print(f"Wilayas with ALL coordinates collapsed to a single point: {len(bad_wilayas)}")
for bw in bad_wilayas:
    print(f"  Wilaya {bw[0]} ({bw[1]}): {bw[2]} facilities all at ({bw[3]}, {bw[4]})")

