#!/usr/bin/env Python3
"""
Phase 5 — Investiguer les anomalies détectées par l'audit.
- 4 téléphones invalides
- 573 notes invalides
- 1,059 adresses vides
- 4 GPS hors Algérie
"""
import sqlite3, sys, csv
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1. Invalid phones
print("=== TÉLÉPHONES INVALIDES (4) ===")
cur.execute("""
    SELECT nom, wilaya, telephone, google_maps_url
    FROM places 
    WHERE telephone IS NOT NULL AND telephone != ''
      AND telephone NOT GLOB '0[0-9]*'
      AND telephone NOT GLOB '+213[0-9]*'
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  Nom: {row[0][:40]}")
    print(f"  Téléphone: '{row[2]}'")
    print(f"  Wilaya: {row[1]}")
    print()

# 2. Invalid notes
print("\n=== NOTES INVALIDES (573) - Sample ===")
cur.execute("""
    SELECT nom, wilaya, note
    FROM places 
    WHERE note IS NOT NULL AND note != ''
      AND (note NOT GLOB '[0-9][0-9.]*' OR CAST(note AS REAL) < 0 OR CAST(note AS REAL) > 5)
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  Nom: {row[0][:40]}")
    print(f"  Note: '{row[2]}'")
    print(f"  Wilaya: {row[1]}")
    print()

# Get distribution of invalid note values
cur.execute("""
    SELECT note, COUNT(*) as cnt
    FROM places 
    WHERE note IS NOT NULL AND note != ''
      AND (note NOT GLOB '[0-9][0-9.]*' OR CAST(note AS REAL) < 0 OR CAST(note AS REAL) > 5)
    GROUP BY note
    ORDER BY cnt DESC
    LIMIT 10
""")
print("  Distribution des valeurs de notes invalides:")
for row in cur.fetchall():
    print(f"    '{row[0]}': {row[1]}")

# 3. Check phone format issues
cur.execute("""
    SELECT telephone, COUNT(*) as cnt
    FROM places 
    WHERE telephone IS NOT NULL AND telephone != ''
      AND telephone NOT GLOB '0[0-9]*'
      AND telephone NOT GLOB '+213[0-9]*'
    GROUP BY telephone
    ORDER BY cnt DESC
    LIMIT 10
""")
print("\n  Distribution des téléphones invalides:")
for row in cur.fetchall():
    print(f"    '{row[0]}': {row[1]}")

# 4. Addresses empty - distribution by wilaya
print("\n=== ADRESSES VIDES (1,059) - Top 10 wilayas ===")
cur.execute("""
    SELECT wilaya, COUNT(*) as cnt
    FROM places 
    WHERE adresse IS NULL OR adresse = ''
    GROUP BY wilaya 
    ORDER BY cnt DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# 5. Invalid URLs
print("\n=== URLs INVALIDES (1) ===")
cur.execute("""
    SELECT nom, wilaya, google_maps_url, adresse
    FROM places 
    WHERE google_maps_url IS NULL 
      OR google_maps_url = '' 
      OR (google_maps_url NOT LIKE 'http%' AND google_maps_url NOT LIKE 'https%')
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"  Nom: {row[0][:40]}")
    print(f"  Wilaya: {row[1]}")
    print(f"  URL: '{row[2][:80] if row[2] else 'NULL'}'")
    print(f"  Adresse: '{row[3][:60] if row[3] else 'NULL'}'")
    print()

# 6. Check checkpoint for same entries to see if enrichment is possible
print("\n=== Vérification enrichment possibile depuis checkpoint ===")
# Read checkpoint
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    ckpt_rows = list(reader)

# Build URL -> checkpoint row map
ckpt_map = {}
for r in ckpt_rows:
    url = r.get('google_maps_url', '').strip()
    if url:
        ckpt_map[url] = r

# Check invalid phones in checkpoint
invalid_phone_db = []
cur.execute("""
    SELECT nom, wilaya, telephone, google_maps_url
    FROM places 
    WHERE telephone IS NOT NULL AND telephone != ''
      AND telephone NOT GLOB '0[0-9]*'
      AND telephone NOT GLOB '+213[0-9]*'
""")
for row in cur.fetchall():
    url = row[3]
    if url in ckpt_map:
        ckpt_tel = ckpt_map[url].get('telephone', '').strip()
        if ckpt_tel and ckpt_tel != row[2]:
            invalid_phone_db.append({
                'nom': row[0],
                'db_phone': row[2],
                'ckpt_phone': ckpt_tel,
                'url': url
            })

print(f"Invalid phones with different value in checkpoint: {len(invalid_phone_db)}")
for r in invalid_phone_db[:5]:
    print(f"  {r['nom'][:30]}: DB='{r['db_phone']}' vs CKPT='{r['ckpt_phone']}'")

# Check invalid notes in checkpoint
cur.execute("""
    SELECT nom, note, google_maps_url
    FROM places 
    WHERE note IS NOT NULL AND note != ''
      AND (note NOT GLOB '[0-9][0-9.]*' OR CAST(note AS REAL) < 0 OR CAST(note AS REAL) > 5)
""")
invalid_note_db = []
for row in cur.fetchall():
    url = row[2]
    if url in ckpt_map:
        ckpt_note = ckpt_map[url].get('note', '').strip()
        invalid_note_db.append({
            'nom': row[0],
            'db_note': row[1],
            'ckpt_note': ckpt_note
        })

print(f"\nInvalid notes found in checkpoint: {len(invalid_note_db)}")
for r in invalid_note_db[:5]:
    print(f"  {r['nom'][:30]}: DB='{r['db_note']}' vs CKPT='{r['ckpt_note']}'")

conn.close()
