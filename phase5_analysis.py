#!/usr/bin/env Python3
"""
Phase 5 — Étape 2 & 3: 
- Analyse communes: examiner les GPS pour proposer une solution de géocodage inverse
- Analyse CANDIDATE: examiner les 935 entrées, URLs valides, sources fiables

NE MODIFIE AUCUNE DONNÉE — lecture seule.
"""
import csv, sqlite3, sys, json
from pathlib import Path
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
SEPT_CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'

results = {
    'commune_analysis': {},
    'candidate_analysis': {},
}

# ============================================================================
# ÉTAPE 2: Analyse communes
# ============================================================================
print("=== ÉTAPE 2: ANALYSE COMMUNES — GÉOCODAGE INVERSE ===\n")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Count entries with GPS but empty commune
cur.execute("""
    SELECT COUNT(*) FROM places 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL 
      AND (commune IS NULL OR commune = '')
""")
results['commune_analysis']['entries_with_gps_no_commune'] = cur.fetchone()[0]

# Sample GPS coordinates for commune inference
cur.execute("""
    SELECT nom, wilaya, latitude, longitude, categorie_recherche
    FROM places 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL 
      AND (commune IS NULL OR commune = '')
""")
gps_samples = cur.fetchall()

# Group by wilaya to see coverage needed
wilaya_gps = Counter(r[4] for r in gps_samples)  # by wilaya
print(f"Entries with GPS but no commune: {results['commune_analysis']['entries_with_gps_no_commune']}")

# Show wilaya distribution
print(f"\nDistribution par wilaya (top 10):")
for w, count in Counter(r[1] for r in gps_samples).most_common(10):
    print(f"  {w}: {count}")

# Show GPS range per wilaya to assess geocoding feasibility
print(f"\nGPS bounds sample (first 10):")
for i, r in enumerate(gps_samples[:10]):
    print(f"  {r[0][:30]} ({r[1]}): lat={r[2]:.4f}, lng={r[3]:.4f}, cat={r[4]}")

results['commune_analysis']['gps_samples'] = [
    {'nom': r[0][:50], 'wilaya': r[1], 'lat': r[2], 'lng': r[3], 'cat': r[4]}
    for r in gps_samples[:20]
]

# Check if communes_officielles module can help
try:
    from communes_officielles import get_all_communes, get_communes_by_wilaya
    all_communes = get_all_communes()
    results['commune_analysis']['official_communes_available'] = len(all_communes)
    print(f"\nCommunes officielles disponibles: {len(all_communes)}")
    
    # Check if any DB entries have commune set
    cur.execute("SELECT COUNT(*) FROM places WHERE commune IS NOT NULL AND commune != ''")
    db_commune_count = cur.fetchone()[0]
    results['commune_analysis']['entries_with_commune_in_db'] = db_commune_count
    print(f"Entries with commune in DB: {db_commune_count}")
    
except ImportError as e:
    print(f"Cannot import communes_officielles: {e}")
    results['commune_analysis']['official_communes_available'] = 0

# Geocoding solution analysis
print(f"\nGeocoding solution analysis:")
print(f"  - Need to map {results['commune_analysis']['entries_with_gps_no_commune']} GPS points to communes")
print(f"  - Algerie's 1541 official communes can be used as polygons")
print(f"  - Solution: use a point-in-polygon approach with commune boundary data")
print(f"  - Free options: Nominatim (OpenStreetMap), GeoPy")
print(f"  - Limitation: requires commune polygon data (not currently in project)")

results['commune_analysis']['geocoding_recommendation'] = {
    'approach': 'point_in_polygon with official commune boundaries',
    'data_needed': 'Commune boundary polygon GeoJSON (not currently in project)',
    'free_options': ['Nominatim OSM reverse geocoding', 'GeoPy with OpenStreetMap'],
    'limitation': 'Would need to add commune polygon data to project; existing GPS coordinates for 4 entries are wrong (outside Algeria)',
    'estimated_entries_affected': results['commune_analysis']['entries_with_gps_no_commune'],
}

# ============================================================================
# ÉTAPE 3: Analyse CANDIDATE
# ============================================================================
print("\n=== ÉTAPE 3: ANALYSE CANDIDATE (935 entrées) ===\n")

# Read checkpoint and extract CANDIDATE entries
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    ckpt_rows = list(reader)

candidates = [r for r in ckpt_rows if r.get('name_status', 'VERIFIED') == 'CANDIDATE']
print(f"Total CANDIDATE entries in checkpoint: {len(candidates)}")

# Check URL validity
valid_urls = [r for r in candidates if r.get('google_maps_url', '').strip() and 
              r.get('google_maps_url', '').strip().startswith('http')]
invalid_urls = [r for r in candidates if not valid_urls]

print(f"  Valid URLs: {len(valid_urls)}")
print(f"  Empty/invalid URLs: {len([r for r in candidates if not r.get('google_maps_url', '').strip()])}")

# Check GPS data
with_gps = [r for r in candidates if r.get('latitude', '').strip() and r.get('longitude', '').strip()]
without_gps = [r for r in candidates if not r.get('latitude', '').strip() or not r.get('longitude', '').strip()]
print(f"  With GPS: {len(with_gps)}")
print(f"  Without GPS: {len(without_gps)}")

# Check phone data
with_phone = [r for r in candidates if r.get('telephone', '').strip()]
with_note = [r for r in candidates if r.get('note', '').strip()]
with_url_in_sept = 0
with_url_in_checkpoint = 0

# Build September checkpoint URL map
with open(SEPT_CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    sept_reader = csv.DictReader(f)
    sept_rows = list(sept_reader)
    sept_map = {r['google_maps_url']: r for r in sept_rows if r.get('google_maps_url', '').strip()}

for r in candidates:
    url = r.get('google_maps_url', '').strip()
    if url and url in sept_map:
        with_url_in_sept += 1
    if url and url in ckpt_rows:  # check main checkpoint
        with_url_in_checkpoint += 1

# Check September for valid names
recovered_from_sept = 0
for r in candidates:
    url = r.get('google_maps_url', '').strip()
    if url in sept_map:
        sept_row = sept_map[url]
        sept_nom = sept_row.get('nom', '').strip()
        if sept_nom and 'impossible' not in sept_nom.lower() and 'erreur' not in sept_nom.lower():
            recovered_from_sept += 1

print(f"\n  With phone: {len(with_phone)}")
print(f"  With note: {len(with_note)}")
print(f"  URL found in September checkpoint: {with_url_in_sept}")
print(f"  September checkpoint has valid name for URL: {recovered_from_sept}")

# Wilaya distribution
wilaya_dist = Counter(r.get('wilaya', 'INCONNU') for r in candidates)
print(f"\n  Distribution par wilaya (top 10):")
for w, c in wilaya_dist.most_common(10):
    print(f"    {w}: {c}")

# Sample candidates
print(f"\n  Sample CANDIDATE entries:")
for r in candidates[:5]:
    url = r.get('google_maps_url', '').strip()
    has_sept = url in sept_map if url else False
    sept_nom = ''
    if has_sept:
        sept_nom = sept_map[url].get('nom', '')[:30]
    print(f"    Nom: {r.get('nom', '')[:40]}")
    print(f"    Wilaya: {r.get('wilaya', '')}")
    print(f"    Catégorie: {r.get('categorie_recherche', '')}")
    print(f"    Tel: {r.get('telephone', '')}")
    print(f"    GPS: {r.get('latitude', '')}, {r.get('longitude', '')}")
    print(f"    September URL found: {has_sept}, September nom: {sept_nom}")
    print()

results['candidate_analysis'] = {
    'total': len(candidates),
    'with_gps': len(with_gps),
    'without_gps': len(without_gps),
    'with_phone': len(with_phone),
    'with_note': len(with_note),
    'url_in_september': with_url_in_sept,
    'recoverable_from_september': recovered_from_sept,
    'wilaya_distribution': dict(wilaya_dist.most_common(15)),
    'samples': [
        {
            'nom': r.get('nom', '')[:50],
            'wilaya': r.get('wilaya', ''),
            'categorie': r.get('categorie_recherche', ''),
            'telephone': r.get('telephone', ''),
            'latitude': r.get('latitude', ''),
            'longitude': r.get('longitude', ''),
            'url': r.get('google_maps_url', '')[:80],
        }
        for r in candidates[:10]
    ],
}

# Write JSON results
report_path = Path(r'D:\SANTE_DZ_EXPORTS\phase5_analysis.json')
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
print(f"\nRapport JSON: {report_path}")

conn.close()
print("\n=== ANALYSE TERMINÉE (Lecture seule — aucune modification de données) ===")
