#!/usr/bin/env Python3
"""
Phase 4.2: Import enrichment entries with valid names that aren't already in DB.
These are entries from September enrichment that were missed in the main checkpoint.
"""
import csv, sqlite3, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ENRICHMENT = r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv'
DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
DB_BACKUP = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_enrich_import.db'

ERROR_PATTERNS = ['impossible d', 'erreur de connexion', 'timeout', 'captcha',
                   'page introuvable', 'accès refusé', 'service indisponible']

def is_error_artifact(name):
    text = name.lower().strip()
    for p in ERROR_PATTERNS:
        if p in text:
            return True
    return False

# Get DB URLs and place_ids
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT google_maps_url FROM places")
db_urls = set(r[0] for r in cur.fetchall() if r[0])
cur.execute("SELECT place_id FROM places")
db_place_ids = set(r[0] for r in cur.fetchall() if r[0])
cur.execute("SELECT COUNT(*) FROM places")
db_count_before = cur.fetchone()[0]
conn.close()

print(f"DB entries before: {db_count_before}")
print(f"DB URLs: {len(db_urls)}")
print(f"DB place_ids: {len(db_place_ids)}")

# Load enrichment data
with open(ENRICHMENT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    enrich_rows = list(reader)

print(f"\nEnrichment rows: {len(enrich_rows)}")

# Find entries that:
# 1. Have valid names (not error artifacts)
# 2. Have URL not in DB (not already imported)
# 3. Have valid place_id not in DB (not duplicate)
# 4. Have GPS coordinates
new_entries = []
for r in enrich_rows:
    url = r.get('google_maps_url', '').strip()
    pid = r.get('place_id_si_visible', '').strip()
    nom = r.get('nom', '').strip()
    lat = r.get('latitude', '').strip()
    lng = r.get('longitude', '').strip()
    
    if is_error_artifact(nom):
        continue
    if not url or url in db_urls:
        continue
    if not pid or pid in db_place_ids:
        continue
    if not lat or not lng:
        continue
    
    new_entries.append(r)

print(f"New entries to import (valid name, unique URL, unique place_id, has GPS): {len(new_entries)}")

# Show samples
print(f"\n=== Sample new entries ===")
for r in new_entries[:5]:
    print(f"  Nom: {r.get('nom', '')[:50]}")
    print(f"  Wilaya: {r.get('wilaya', '')}")
    print(f"  Catégorie: {r.get('categorie_recherche', '')}")
    print(f"  Tel: {r.get('telephone', '')}")
    print(f"  GPS: {r.get('latitude', '')}, {r.get('longitude', '')}")
    print(f"  URL: {r.get('google_maps_url', '')[:60]}")
    print()

# Now import these entries
# Backup DB first
import shutil
shutil.copy2(DB_PATH, DB_BACKUP)
print(f"\nBackup created: {DB_BACKUP}")

# Import
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

imported = 0
for r in new_entries:
    try:
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
            r.get("place_id_si_visible", "").strip() or None,
            r.get("nom", "").strip(),
            r.get("nom", "").strip().lower(),
            r.get("adresse", "").strip() if r.get('adresse', '').strip() != 'Itinéraires' else None,
            (r.get("adresse", "").strip() if r.get('adresse', '').strip() != 'Itinéraires' else '').lower(),
            r.get("telephone", "").strip(),
            None,
            r.get("telephone", "").strip(),
            r.get("site_web", "").strip(),
            r.get("note", "").strip(),
            r.get("nombre_avis", "").strip(),
            r.get("horaires", "").strip() if r.get('horaires', '').strip() != 'Itinéraires' else None,
            float(r["latitude"]) if r.get("latitude", "").strip() else None,
            float(r["longitude"]) if r.get("longitude", "").strip() else None,
            r.get("google_maps_url", "").strip(),
            r.get("type_google", "").strip(),
            r.get("wilaya", "").strip(),
            r.get("wilaya", "").strip().lower(),
            r.get("commune", "").strip(),
            r.get("categorie_recherche", "").strip(),
            r.get("source", "").strip(),
            r.get("scrape_date", "").strip(),
            "ENRICHMENT_RECOVERED",
            "checkpoint_enrichment.csv_2026-10-10",
            "2026-10-10",
        ))
        imported += 1
    except Exception as e:
        print(f"Error importing {r.get('nom', '')[:30]}: {e}")

conn.commit()

# Verify
cur.execute("SELECT COUNT(*) FROM places")
db_count_after = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM places WHERE name_status = 'ENRICHMENT_RECOVERED'")
enrichment_count = cur.fetchone()[0]

print(f"\n=== Import complete ===")
print(f"Entries imported: {imported}")
print(f"DB total before: {db_count_before}")
print(f"DB total after: {db_count_after}")
print(f"ENRICHMENT_RECOVERED entries: {enrichment_count}")

# Verify no artifacts
cur.execute("SELECT COUNT(*) FROM places WHERE nom LIKE '%impossible%' OR nom LIKE '%erreur%'")
artifacts = cur.fetchone()[0]
print(f"Error artifacts in DB: {artifacts}")

conn.close()
