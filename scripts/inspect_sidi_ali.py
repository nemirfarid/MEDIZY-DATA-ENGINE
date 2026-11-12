import sqlite3

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()

# Search Sidi Ali Mostaganem
query = """
SELECT id, nom, categorie, commune, wilaya, latitude, longitude 
FROM facilities 
WHERE wilaya LIKE '%Mostaganem%' 
  AND (commune LIKE '%Sidi Ali%' OR nom LIKE '%Sidi Ali%' OR adresse LIKE '%Sidi Ali%')
"""
rows = cur.execute(query).fetchall()
print(f"Total matching 'Sidi Ali' in bundled DB: {len(rows)}")
for r in rows:
    print(r)

# Check total Mostaganem in bundled DB
mosta_count = cur.execute("SELECT count(*) FROM facilities WHERE wilaya LIKE '%Mostaganem%'").fetchone()[0]
print(f"Total facilities in Mostaganem in bundled DB: {mosta_count}")

