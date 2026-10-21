#!/usr/bin/env Python3
"""
Phase 5 — Update geocoding for new entries.
Only assigns communes to entries that don't have one yet.
Idempotent — skips entries already geocoded.
"""
import sqlite3, sys, math, json
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
ALGERIA_LAT_MIN, ALGERIA_LAT_MAX = 19.5, 37.5
ALGERIA_LNG_MIN, ALGERIA_LNG_MAX = -8.5, 12.0
HIGH_KM = 5.0

sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')
from communes_officielles import get_all_communes
from communes_algerie import WILAYAS

# Load communes
all_communes = get_all_communes()
communes_with_gps = [c for c in all_communes if c.get('latitude') and c.get('longitude')]
communes_by_wilaya = {}
for c in communes_with_gps:
    communes_by_wilaya.setdefault(c.get('wilaya_code', ''), []).append(c)

wilaya_name_to_code = {}
for w in WILAYAS:
    name = (w.get('nom') or '').lower()
    code = w.get('code')
    if name and code:
        wilaya_name_to_code[name] = code

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Get entries without commune that have valid GPS
cur.execute("""
    SELECT id, nom, latitude, longitude, wilaya
    FROM places 
    WHERE (commune IS NULL OR commune = '')
      AND latitude IS NOT NULL AND longitude IS NOT NULL
      AND latitude BETWEEN ? AND ?
      AND longitude BETWEEN ? AND ?
""", (ALGERIA_LAT_MIN, ALGERIA_LAT_MAX, ALGERIA_LNG_MIN, ALGERIA_LNG_MAX))

entries = cur.fetchall()
print(f"Entries needing geocoding: {len(entries)}")

timestamp = datetime.now().isoformat()
source_label = f"geocoding_centroid_officiel_v1_{timestamp[:10]}"

applied = 0
low_confidence = 0

for row in entries:
    db_id, nom, lat, lng, wilaya = row
    wilaya_lower = (wilaya or '').lower()
    wcode = wilaya_name_to_code.get(wilaya_lower)
    
    if not wcode:
        continue
    
    wcommunes = communes_by_wilaya.get(wcode, [])
    if not wcommunes:
        continue
    
    best_dist = float('inf')
    best_commune = None
    for c in wcommunes:
        dist = haversine(lat, lng, c['latitude'], c['longitude'])
        if dist < best_dist:
            best_dist = dist
            best_commune = c
    
    if best_commune and best_dist < HIGH_KM:
        cur.execute("""
            UPDATE places 
            SET commune = ?, commune_source = ?, commune_confidence = ?, commune_updated_at = ?
            WHERE id = ?
        """, (
            best_commune['nom_fr'],
            source_label,
            best_dist,
            timestamp,
            db_id,
        ))
        applied += 1
    else:
        low_confidence += 1

conn.commit()

cur.execute("SELECT COUNT(*) FROM places WHERE commune IS NOT NULL AND commune != ''")
with_commune = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM places")
total = cur.fetchone()[0]

print(f"\n=== Géocodage mis à jour ===")
print(f"Entrées géocodées (HIGH confidence): {applied}")
print(f"Entrées en attente (LOW confidence): {low_confidence}")
print(f"Total entrées avec commune: {with_commune}/{total} ({with_commune/total*100:.1f}%)")

conn.close()
