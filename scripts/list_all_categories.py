import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT categorie, count(1) FROM facilities GROUP BY categorie ORDER BY count(1) DESC")
rows = c.fetchall()
print(f"Total distinct categories: {len(rows)}")
for r in rows:
    print(r)

conn.close()

