#!/usr/bin/env Python3
"""
Phase 5 — Correction des anomalies détectées par l'audit.
1. Normalisation des 4 téléphones mal formatés
2. Investigation des 4 GPS hors Algérie (vérifier September checkpoint)
3. Tentative de récupération d'adresses vides depuis le checkpoint
"""
import sqlite3, csv, sys, shutil, json
from datetime import datetime
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
SEPT_CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'
DB_BACKUP = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_phase5_fixes.db'

# Alger coordinate bounds
ALGERIA_LAT_MIN, ALGERIA_LAT_MAX = 19.5, 37.5
ALGERIA_LNG_MIN, ALGERIA_LNG_MAX = -8.5, 12.0

# Import phone normalization
sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')
from normalization import normalize_phone_raw

# Load September checkpoint for GPS recovery
print("Loading September checkpoint for GPS recovery...")
with open(SEPT_CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    sept_rows = list(reader)
    sept_dict = {r['google_maps_url']: r for r in sept_rows if r.get('google_maps_url', '').strip()}

# Load checkpoint for address recovery
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    ckpt_rows = list(reader)
    ckpt_dict = {r['google_maps_url']: r for r in ckpt_rows if r.get('google_maps_url', '').strip()}

# Backup DB
shutil.copy2(DB_PATH, DB_BACKUP)
print(f"Backup créé: {DB_BACKUP}")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ============================================================================
# 1. Fix invalid phone numbers
# ============================================================================
print("\n=== 1. CORRECTION DES TÉLÉPHONES ===")

cur.execute("""
    SELECT id, nom, wilaya, telephone, google_maps_url
    FROM places 
    WHERE telephone IS NOT NULL AND telephone != ''
      AND telephone NOT GLOB '0[0-9]*'
      AND telephone NOT GLOB '+213[0-9]*'
""")
invalid_phones = cur.fetchall()

phone_fixes = 0
for row in invalid_phones:
    db_id, nom, wilaya, old_phone, url = row
    normalized = normalize_phone_raw(old_phone)
    
    if normalized and normalized != old_phone:
        # Check if normalized is valid Algerian format
        if normalized.startswith('+213') or (normalized.startswith('0') and len(normalized) >= 10):
            cur.execute("UPDATE places SET telephone = ?, telephone_raw = ? WHERE id = ?", 
                       (normalized, old_phone, db_id))
            phone_fixes += 1
            print(f"  [{nom[:30]}] '{old_phone}' -> '{normalized}'")
        else:
            print(f"  [{nom[:30]}] '{old_phone}' -> '{normalized}' (still invalid, kept as-is)")

if phone_fixes == 0:
    print("  No phone fixes needed")
conn.commit()
print(f"  Total phones normalized: {phone_fixes}")

# ============================================================================
# 2. Investigate and fix GPS coordinates
# ============================================================================
print("\n=== 2. INVESTIGATION GPS HORS ALGÉRIE ===")

ERROR_PATTERNS = ['impossible d', 'erreur de connexion', 'timeout', 'captcha',
                   'page introuvable', 'accès refusé', 'service indisponible']

cur.execute("""
    SELECT id, nom, wilaya, latitude, longitude, google_maps_url, place_id, note
    FROM places 
    WHERE latitude IS NOT NULL 
      AND longitude IS NOT NULL
      AND (latitude < ? OR latitude > ? OR longitude < ? OR longitude > ?)
""", (ALGERIA_LAT_MIN, ALGERIA_LAT_MAX, ALGERIA_LNG_MIN, ALGERIA_LNG_MAX))

bad_gps = cur.fetchall()
gps_fixed = 0

for entry in bad_gps:
    db_id, nom, wilaya, lat, lng, url, pid, note = entry
    print(f"\n  [{nom[:40]}] Wilaya: {wilaya}")
    print(f"  Current GPS: {lat}, {lng}")
    
    # Check September checkpoint for same URL
    if url and url in sept_dict:
        sept = sept_dict[url]
        sept_lat = sept.get('latitude', '').strip()
        sept_lng = sept.get('longitude', '').strip()
        sept_nom = sept.get('nom', '').strip()
        
        if sept_lat and sept_lng:
            try:
                slat = float(sept_lat)
                slng = float(sept_lng)
                if ALGERIA_LAT_MIN <= slat <= ALGERIA_LAT_MAX and ALGERIA_LNG_MIN <= slng <= ALGERIA_LNG_MAX:
                    print(f"  September GPS found: {slat}, {slng} (in Algeria zone)")
                    print(f"  September nom: {sept_nom[:50]}")
                    if sept_nom and not any(p in sept_nom.lower() for p in ERROR_PATTERNS):
                        # Update GPS and name if September has better data
                        cur.execute("UPDATE places SET latitude = ?, longitude = ? WHERE id = ?",
                                   (slat, slng, db_id))
                        gps_fixed += 1
                        print(f"  -> GPS FIXED to September values")
                    else:
                        print(f"  -> September name also artifact, not fixing")
                else:
                    print(f"  September GPS also outside Algeria: {slat}, {slng}")
            except ValueError:
                print(f"  September GPS invalid format: {sept_lat}, {sept_lng}")
        else:
            print(f"  September has no GPS coordinates")
    else:
        print(f"  URL not found in September checkpoint")
    
    # Check checkpoint.csv for same entry
    if url and url in ckpt_dict:
        ckpt = ckpt_dict[url]
        ckpt_lat = ckpt.get('latitude', '').strip()
        ckpt_lng = ckpt.get('longitude', '').strip()
        if ckpt_lat and ckpt_lng:
            try:
                clat = float(ckpt_lat)
                clng = float(ckpt_lng)
                print(f"  Checkpoint GPS: {clat}, {clng}")
            except ValueError:
                pass
    print(f"  Action needed: verify correct GPS for this establishment")

conn.commit()
print(f"\n  GPS coordinates fixed: {gps_fixed}")

if gps_fixed == 0:
    print("  No GPS fixes possible (September checkpoint also had wrong coordinates)")
    print("  RECOMMENDATION: These 4 entries need manual verification or re-scraping")

# ============================================================================
# 3. Attempt address recovery from checkpoint
# ============================================================================
print("\n=== 3. RÉCUPÉRATION D'ADRESSES VIDES ===")

cur.execute("""
    SELECT COUNT(*) FROM places WHERE adresse IS NULL OR adresse = ''
""")
empty_addr_count = cur.fetchone()[0]
print(f"Total empty addresses: {empty_addr_count}")

address_recovered = 0
for i in range(0, empty_addr_count, 1000):
    cur.execute("""
        SELECT id, google_maps_url FROM places 
        WHERE (adresse IS NULL OR adresse = '')
        LIMIT 1000 OFFSET ?
    """, (i,))
    batch = cur.fetchall()
    
    for db_id, url in batch:
        if not url:
            continue
        # Check checkpoint for valid address
        if url in ckpt_dict:
            ckpt_adr = ckpt_dict[url].get('adresse', '').strip()
            if ckpt_adr and ckpt_adr.lower() not in ['itinéraires', 'itineraires', '']:
                cur.execute("UPDATE places SET adresse = ?, adresse_normalized = ? WHERE id = ?",
                           (ckpt_adr, ckpt_adr.lower().strip(), db_id))
                address_recovered += 1
        # Check September checkpoint
        if url in sept_dict:
            sept_adr = sept_dict[url].get('adresse', '').strip()
            if sept_adr and sept_adr.lower() not in ['itinéraires', 'itineraires', '']:
                cur.execute("UPDATE places SET adresse = ?, adresse_normalized = ? WHERE id = ?",
                           (sept_adr, sept_adr.lower().strip(), db_id))
                address_recovered += 1

conn.commit()
print(f"Addresses recovered from checkpoint/September: {address_recovered}")

# Re-check
cur.execute("""
    SELECT COUNT(*) FROM places WHERE adresse IS NULL OR adresse = ''
""")
remaining_empty = cur.fetchone()[0]
print(f"Remaining empty addresses: {remaining_empty}")

# ============================================================================
# Summary
# ============================================================================
conn.close()

print(f"\n=== RÉSUMÉ DES CORRECTIONS ===")
print(f"Phones normalized: {phone_fixes}")
print(f"GPS coordinates fixed: {gps_fixed} (4 entries need manual verification)")
print(f"Addresses recovered: {address_recovered}")
print(f"Backups: {DB_BACKUP}")
