#!/usr/bin/env Python3
"""
Phase 5 — Étape 3: Import correct des 935 noms CANDIDATE.
Lit directement le checkpoint, extrait les noms depuis les URLs complètes,
vérifie l'unicité, et importe.
"""
import sqlite3, csv, sys, urllib.parse, re, shutil
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
DB_BACKUP = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_candidate_import_v2.db'
CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
OUTPUT_CSV = r'D:\SANTE_DZ_EXPORTS\candidate_import_log.csv'

ERROR_PATTERNS = ['impossible d', 'erreur de connexion', 'timeout', 'captcha',
                   'page introuvable', 'accès refusé', 'service indisponible']

def extract_name_from_url(url):
    """Extract establishment name from Google Maps URL."""
    if not url or not url.startswith('http'):
        return None
    match = re.search(r'/place/([^/]+?)(?:/data=|/$)', url)
    if match:
        raw = match.group(1)
        decoded = urllib.parse.unquote_plus(raw)
        if decoded.startswith('data=') or 'data=' in decoded:
            return None
        if decoded.startswith('CID_') or decoded.startswith('ChIJ'):
            return None
        if any(p in decoded.lower() for p in ERROR_PATTERNS):
            return None
        if len(decoded) >= 3 and not decoded.replace(' ', '').isdigit():
            return decoded.strip()
    return None

# Load CANDIDATE entries from checkpoint
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    ckpt_rows = list(reader)

candidates = [r for r in ckpt_rows if r.get('name_status', 'VERIFIED') == 'CANDIDATE']
print(f"CANDIDATE entries in checkpoint: {len(candidates)}")

# Extract names from URLs
extracted = []
for r in candidates:
    url = r.get('google_maps_url', '').strip()
    name = extract_name_from_url(url)
    if name and not any(p in name.lower() for p in ERROR_PATTERNS):
        extracted.append({
            'row': r,
            'url': url,
            'extracted_name': name,
        })

print(f"Names extracted from URLs: {len(extracted)}")

# Get DB state
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT google_maps_url FROM places WHERE google_maps_url IS NOT NULL AND google_maps_url != ''")
db_urls = set(r[0] for r in cur.fetchall())
cur.execute("SELECT place_id FROM places WHERE place_id IS NOT NULL AND place_id != ''")
db_pids = set(r[0] for r in cur.fetchall())
cur.execute("SELECT COUNT(*) FROM places")
db_before = cur.fetchone()[0]

# Deduplicate within extracted set (by URL)
unique_by_url = {}
internal_dups_url = 0
for e in extracted:
    url = e['url']
    if url in unique_by_url:
        internal_dups_url += 1
    else:
        unique_by_url[url] = e

# Deduplicate by place_id
unique_by_pid = {}
internal_dups_pid = 0
for e in extracted:
    pid = e['row'].get('place_id_si_visible', '').strip()
    if pid:
        if pid in unique_by_pid:
            internal_dups_pid += 1
        else:
            unique_by_pid[pid] = e

print(f"Internal duplicates by URL: {internal_dups_url}")
print(f"Internal duplicates by place_id: {internal_dups_pid}")

# Find truly new entries (not in DB)
to_import = []
in_db_url = 0
in_db_pid = 0
for e in unique_by_url.values():
    url = e['url']
    pid = e['row'].get('place_id_si_visible', '').strip()
    
    if url in db_urls:
        in_db_url += 1
        continue
    if pid and pid in db_pids:
        in_db_pid += 1
        continue
    
    to_import.append(e)

print(f"\nEntries to import:")
print(f"  New unique URLs: {len(to_import)}")
print(f"  Already in DB (by URL): {in_db_url}")
print(f"  Already in DB (by place_id): {in_db_pid}")

# Normalize phone function
from normalization import normalize_phone_raw

# Backup
shutil.copy2(DB_PATH, DB_BACKUP)
print(f"\nBackup créé: {DB_BACKUP}")

# Import with transaction
try:
    timestamp = datetime.now().isoformat()
    source_label = f"url_extraction_2026-10-10"
    log_entries = []
    imported = 0
    
    for e in to_import:
        r = e['row']
        url = e['url']
        pid = r.get('place_id_si_visible', '').strip() or None
        
        tel = r.get('telephone', '').strip()
        if tel and not tel.startswith('+213') and not tel.startswith('0'):
            tel = normalize_phone_raw(tel)
        
        # Check if name already exists in DB with same GPS (true duplicate)
        lat = float(r['latitude']) if r.get('latitude', '').strip() else None
        lng = float(r['longitude']) if r.get('longitude', '').strip() else None
        
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
            r.get('adresse', '').strip() if r.get('adresse', '').strip().lower() not in ['itinéraires', '', 'NULL'] else None,
            r.get('adresse', '').strip().lower() if r.get('adresse', '').strip().lower() not in ['itinéraires', '', 'NULL'] else '',
            tel or None,
            None,
            tel,
            r.get('site_web', '').strip() or None,
            r.get('note', '').strip() or None,
            r.get('nombre_avis', '').strip() or None,
            r.get('horaires', '').strip() if r.get('horaires', '').strip().lower() not in ['itinéraires', '', 'NULL'] else None,
            lat,
            lng,
            url,
            r.get('type_google', '').strip() or None,
            r.get('wilaya', '').strip(),
            r.get('wilaya', '').strip().lower(),
            None,
            r.get('categorie_recherche', '').strip(),
            'Google Maps public UI',
            r.get('scrape_date', '').strip(),
            'VERIFIED',
            source_label,
            timestamp[:10],
        ))
        imported += 1
        log_entries.append({
            'id': cur.lastrowid,
            'nom': e['extracted_name'][:60],
            'wilaya': r.get('wilaya', ''),
            'url': url[:80],
        })
    
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM places")
    db_after = cur.fetchone()[0]
    
    print(f"\n=== IMPORT TERMINÉ ===")
    print(f"DB before: {db_before}")
    print(f"DB after: {db_after}")
    print(f"Entries imported: {db_after - db_before}")
    print(f"Log entries: {len(log_entries)}")
    
    # Verify no artifacts
    cur.execute("SELECT COUNT(*) FROM places WHERE nom LIKE '%impossible%' OR nom LIKE '%erreur%'")
    artifacts = cur.fetchone()[0]
    print(f"Error artifacts in DB: {artifacts}")
    
    # Verify duplicates
    cur.execute("SELECT COUNT(*) FROM (SELECT google_maps_url FROM places GROUP BY google_maps_url HAVING COUNT(*) > 1)")
    dup_urls = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM (SELECT place_id FROM places WHERE place_id IS NOT NULL GROUP BY place_id HAVING COUNT(*) > 1)")
    dup_pids = cur.fetchone()[0]
    print(f"Duplicate URLs: {dup_urls}")
    print(f"Duplicate place_ids: {dup_pids}")
    
    # Write log
    with open(OUTPUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'nom', 'wilaya', 'url'])
        writer.writeheader()
        writer.writerows(log_entries)
    print(f"Log written: {OUTPUT_CSV}")

except Exception as ex:
    conn.rollback()
    print(f"ERREUR - transaction annulée: {ex}")
    import traceback
    traceback.print_exc()

conn.close()
