import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

wilayas = c.execute("SELECT DISTINCT wilaya_code, wilaya FROM facilities ORDER BY wilaya_code").fetchall()
print(f"Total active Wilayas: {len(wilayas)}")
for w_code, w_name in wilayas:
    total_w = c.execute("SELECT count(1) FROM facilities WHERE wilaya_code = ?", (w_code,)).fetchone()[0]
    communes_w = c.execute("SELECT count(DISTINCT commune) FROM facilities WHERE wilaya_code = ?", (w_code,)).fetchone()[0]
    print(f"Wilaya {w_code} ({w_name}): {total_w} structures réelles, {communes_w} communes")

conn.close()

