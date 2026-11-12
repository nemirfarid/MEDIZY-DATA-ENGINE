import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Check duplicates by nom and coordinates rounded to 4 decimals (~11m)
c.execute("""
    SELECT nom, count(1) 
    FROM facilities 
    GROUP BY lower(trim(nom)), round(latitude, 3), round(longitude, 3) 
    HAVING count(1) > 1
""")
dups_coord = c.fetchall()
print(f"Duplicates by name & nearby coords: {len(dups_coord)}")
for d in dups_coord[:10]:
    print("  ", d)

# Check practitioners appearing multiple times across different coordinates
c.execute("""
    SELECT nom, count(1), group_concat(wilaya)
    FROM facilities 
    WHERE lower(nom) LIKE '%dr%' OR lower(nom) LIKE '%docteur%' OR lower(nom) LIKE '%cabinet%'
    GROUP BY lower(trim(nom))
    HAVING count(1) > 1
    ORDER BY count(1) DESC
""")
dups_name = c.fetchall()
print(f"\nPractitioners appearing multiple times with same name: {len(dups_name)}")
for d in dups_name[:15]:
    print("  ", d)

conn.close()

