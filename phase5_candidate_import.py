#!/usr/bin/env Python3
"""
Phase 5 — Étape 3: Vérification et import des 935 CANDIDATE names.
1. Check for duplicates (URL and place_id already in DB)
2. Verify no error artifacts in extracted names
3. Import unique entries into DB
"""
import sqlite3, csv, sys, shutil
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
DB_BACKUP = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_candidate_import.db'
CANDIDATE_CSV = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
EXTRACTED_FILE = r'D:\SANTE_DZ_EXPORTS\candidate_names_extracted.csv'

# Load extracted names
with open(EXTRACTED_FILE, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    extracted = list(reader)

print(f"Extracted names: {len(extracted)}")

# Get DB URLs and place_ids for duplicate check
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT google_maps_url FROM places WHERE google_maps_url IS NOT NULL AND google_maps_url != ''")
db_urls = set(r[0] for r in cur.fetchall())
cur.execute("SELECT place_id FROM places WHERE place_id IS NOT NULL AND place_id != ''")
db_pids = set(r[0] for r in cur.fetchall())
cur.execute("SELECT COUNT(*) FROM places")
db_count_before = cur.fetchone()[0]

print(f"DB URLs: {len(db_urls)}")
print(f"DB place_ids: {len(db_pids)}")

# Also get the original CANDIDATE rows to have full data
with open(CANDIDATE_CSV, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    ckpt_rows = list(reader)

candidates = [r for r in ckpt_rows if r.get('name_status', 'VERIFIED') == 'CANDIDATE']
print(f"CANDIDATE in checkpoint: {len(candidates)}")

# Build candidate URL -> full row
candidate_map = {}
for r in candidates:
    url = r.get('google_maps_url', '').strip()
    if url:
        candidate_map[url] = r

# Check for duplicates
new_entries = []
duplicates_url = 0
duplicates_pid = 0
no_url = 0

for e in extracted:
    url = ''
    # Find the original candidate row to get URL
    for c in candidates:
        if c.get('nom', '') == e.get('nom_original', '') and c.get('wilaya', '') == e.get('wilaya', ''):
            url = c.get('google_maps_url', '').strip()
            break
    
    if not url:
        no_url += 1
        continue
    
    # Check duplicates
    if url in db_urls:
        duplicates_url += 1
        continue
    
    pid = candidate_map.get(url, {}).get('place_id_si_visible', '').strip()
    if pid and pid in db_pids:
        duplicates_pid += 1
        continue
    
    new_entries.append({
        'url': url,
        'candidate': candidate_map.get(url, {}),
        'extracted_name': e['nom_recupere'],
    })

print(f"\n=== Résultats de vérification ===")
print(f"Entrées à importer: {len(new_entries)}")
print(f"Doublons par URL: {duplicates_url}")
print(f"Doublons par place_id: {duplicates_pid}")
print(f"Sans URL: {no_url}")

# Verify no error artifacts in extracted names
ERROR_PATTERNS = ['impossible d', 'erreur de connexion', 'timeout', 'captcha',
                   'page introuvable', 'accès refusé', 'service indisponible']

artifact_names = 0
for e in new_entries:
    name = e['extracted_name'].lower()
    for p in ERROR_PATTERNS:
        if p in name:
            artifact_names += 1
            print(f"  ARTÉFACT: {e['extracted_name'][:40]}")
            break

print(f"\nArtéfacts dans noms extraits: {artifact_names}")

# Show sample of entries to import
print(f"\n=== Échantillon d'entrées à importer (5) ===")
for e in new_entries[:5]:
    c = e['candidate']
    print(f"  Nom (URL): {e['extracted_name'][:50]}")
    print(f"  Wilaya: {c.get('wilaya', '')}")
    print(f"  Catégorie: {c.get('categorie_recherche', '')}")
    print(f"  Tel: {c.get('telephone', '')}")
    print(f"  GPS: {c.get('latitude', '')}, {c.get('longitude', '')}")
    print(f"  Note: {c.get('note', '')}")
    print(f"  URL: {e['url'][:60]}")
    print()

# Backup and import
shutil.copy2(DB_PATH, DB_BACKUP)
print(f"Backup créé: {DB_BACKUP}")

timestamp = datetime.now().isoformat()

try:
    for e in new_entries:
        c = e['candidate']
        url = e['url']
        pid = c.get('place_id_si_visible', '').strip() or None
        
        # Normalize phone if present
        tel = c.get('telephone', '').strip()
        if tel and not tel.startswith('+213') and not tel.startswith('0'):
            # Try normalizing
            from normalization import normalize_phone_raw
            tel = normalize_phone_raw(tel)
        
        cur.execute("""
            INSERT OR IGNORE INTO places (
                place_id, nom, nom_normalized, adresse, adresse_normalized,
                telephone, telephone_normalized, telephone_raw, site_web,
                note, nombre_avis, horaires, latitude, longitude,
                google_maps_url, type_google, wilaya, wilaya_normalized,
                commune, categorie_recherche, source, scrape_date,
                name_status, name_source, recovery_date
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pid,
            e['extracted_name'].strip(),
            e['extracted_name'].strip().lower(),
            c.get('adresse', '').strip() if c.get('adresse', '').strip().lower() not in ['itinéraires', ''] else None,
            (c.get('adresse', '').strip().lower() if c.get('adresse', '').strip().lower() not in ['itinéraires', ''] else ''),
            tel or None,
            None,
            tel,
            c.get('site_web', '').strip() or None,
            c.get('note', '').strip() or None,
            c.get('nombre_avis', '').strip() or None,
            c.get('horaires', '').strip() if c.get('horaires', '').strip().lower() not in ['itinéraires', ''] else None,
            float(c.get('latitude', '')) if c.get('latitude', '').strip() and c.get('latitude', '').strip() != 'NULL' else None,
            float(c.get('longitude', '')) if c.get('longitude', '').strip() and c.get('longitude', '').strip() != 'NULL' else None,
            url,
            c.get('type_google', '').strip() or None,
            c.get('wilaya', '').strip(),
            c.get('wilaya', '').strip().lower(),
            None,  # commune - will be filled by geocoding later
            c.get('categorie_recherche', '').strip(),
            c.get('source', '').strip(),
            c.get('scrape_date', '').strip(),
            'VERIFIED',
            'url_extraction_2026-10-10',
            timestamp[:10],
        ))
    
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM places")
    db_count_after = cur.fetchone()[0]
    print(f"\n=== Import terminé ===")
    print(f"DB before: {db_count_before}")
    print(f"DB after: {db_count_after}")
    print(f"Entries imported: {db_count_after - db_count_before}")
    
    # Verify no artifacts
    cur.execute("SELECT COUNT(*) FROM places WHERE nom LIKE '%impossible%' OR nom LIKE '%erreur%'")
    artifacts = cur.fetchone()[0]
    print(f"Error artifacts in DB: {artifacts}")
    
    # Update GPS for new entries if not already geocoded
    # The new entries might already have commune from geocoding if they were added
    # Let's check
    cur.execute("""
        SELECT COUNT(*) FROM places 
        WHERE name_source = 'url_extraction_2026-10-10'
          AND latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    new_with_gps = cur.fetchone()[0]
    print(f"New entries with GPS: {new_with_gps}")
    
except Exception as e:
    conn.rollback()
    print(f"ERREUR - transaction annulée: {e}")
    import traceback
    traceback.print_exc()

conn.close()
