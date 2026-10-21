import sqlite3

# Check production DB for MIPH_2025 entries
prod = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = prod.cursor()
c.execute("""
    SELECT id, place_id, nom, wilaya, source, latitude, longitude
    FROM places 
    WHERE source = 'MIPH_2025'
    ORDER BY id
""")
rows = c.fetchall()
print(f"MIPH_2025 entries in production: {len(rows)}")
for r in rows:
    print(f"  id={r[0]}, place_id={r[1]}, nom={r[2]}, wilaya={r[3]}, lat={r[5]}, lon={r[6]}")
prod.close()

# Check MIPH CSV
import csv
with open(r'D:\SANTE_DZ_EXPORTS\miph_crossref_new.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    csv_rows = list(reader)

print(f"\nMIPH CSV entries: {len(csv_rows)}")
for r in csv_rows:
    place_id = f"miph_{r['pdf_id']}"
    print(f"  pdf_id={r['pdf_id']}, place_id={place_id}, nom={r['etab_fr']}, wilaya={r['wilaya']}, code_postal={r['code_postal']}")

# Check if place_ids match
print("\n--- Checking place_id collisions ---")
prod = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = prod.cursor()
for r in csv_rows:
    place_id = f"miph_{r['pdf_id']}"
    c.execute('SELECT id, nom FROM places WHERE place_id = ?', (place_id,))
    match = c.fetchone()
    if match:
        print(f"  COLLISION: {place_id} -> DB id={match[0]}, nom={match[1]}")
    else:
        print(f"  NO COLLISION: {place_id} -> would be imported")
prod.close()