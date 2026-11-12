import sqlite3
import gzip
import json
import os

# Connect to the bundled database
db = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = db.cursor()

# Export all facilities as a flat list
c.execute("SELECT id, nom, categorie, specialite, wilaya, wilaya_code, commune, adresse, telephone, latitude, longitude, is_premium, place_id, site_web, note, nombre_avis, source FROM facilities")
rows = c.fetchall()
columns = [d[0] for d in c.description]

facilities_list = []
for row in rows:
    facility = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, bytes):
            val = val.decode('utf-8', errors='replace')
        facility[col] = val
    facilities_list.append(facility)

print(f"Exported {len(facilities_list)} facilities")

# Write gzipped JSON list
output_path = 'assets/data/Annuaire_Sanitaire_National_Algerie_58_Wilayas.json.gz'
json_str = json.dumps(facilities_list, ensure_ascii=False, separators=(',', ':'))
with gzip.open(output_path, 'wb', compresslevel=9) as f:
    f.write(json_str.encode('utf-8'))

size_mb = os.path.getsize(output_path) / (1024 * 1024)
print(f"Wrote {output_path} ({size_mb:.2f} MB)")

db.close()