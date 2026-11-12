import sqlite3
import re

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT id, nom FROM facilities WHERE nom LIKE '%Itinéraires%' OR nom LIKE '%\ue52e%' OR nom LIKE '%\ue934%'")
rows = c.fetchall()
print(f"Structures with UI artifacts in name: {len(rows)}")

def clean_google_name(raw_name):
    if not raw_name:
        return raw_name
    # Remove unicode private use icons
    s = re.sub(r'[\ue000-\uf8ff]', '', raw_name)
    # If the name is duplicated ("Nom Nom 4,5(10) ...")
    # Cut off at rating pattern or 'Itinéraires' or 'Avis' or 'Fermé'
    cut_patterns = [
        r'\s+\d+[,.]\d+\(\d+\).*$',
        r'\s+Aucun avis.*$',
        r'\s+Itinéraires.*$',
        r'\s+Fermé.*$',
        r'\s+Ouvre à.*$',
        r'\s+[A-Z0-9]{4}\+[A-Z0-9]{2,}.*$' # Plus code pattern
    ]
    for p in cut_patterns:
        s = re.sub(p, '', s)
    
    # Check if string has repeated first half
    s = s.strip()
    words = s.split()
    half = len(words) // 2
    if half >= 2 and words[:half] == words[half:half*2]:
        s = " ".join(words[:half])
    return s.strip()

updates = []
for f_id, nom in rows:
    cleaned = clean_google_name(nom)
    if cleaned and cleaned != nom:
        updates.append((cleaned, f_id))

if updates:
    c.executemany("UPDATE facilities SET nom = ? WHERE id = ?", updates)
    conn.commit()
    print(f"Cleaned {len(updates)} structure names!")

# Rebuild view and FTS
c.execute("INSERT INTO facilities_fts(facilities_fts) VALUES('rebuild')")
conn.commit()
print("FTS Rebuilt successfully.")

