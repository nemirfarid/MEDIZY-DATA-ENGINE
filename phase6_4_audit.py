import sqlite3
import hashlib
from collections import defaultdict

# ========== CONFIGURATION ==========
PROD_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
TEST_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db'

ALGERIA_BOUNDS = {'lat_min': 18.9, 'lat_max': 37.1, 'lng_min': -8.7, 'lng_max': 12.0}

def safe(s):
    if s is None:
        return 'NULL'
    return str(s).encode('ascii', 'replace').decode()

# ========== LOAD DATA ==========
print("=" * 80)
print("PHASE 6.4 - AUDIT DE QUALITE ET DE GAIN NATIONAL")
print("=" * 80)

# Load production place_ids and key fields
conn_prod = sqlite3.connect(PROD_DB)
c_prod = conn_prod.cursor()
c_prod.execute('''
    SELECT place_id, nom, nom_normalized, wilaya, commune, categorie_recherche,
           latitude, longitude, telephone, site_web, source
    FROM places WHERE place_id IS NOT NULL
''')
prod_rows = c_prod.fetchall()

prod_by_placeid = {}
prod_by_norm = defaultdict(list)  # normalized name -> list of entries
for row in prod_rows:
    pid, nom, nom_norm, wilaya, commune, cat, lat, lng, phone, website, source = row
    prod_by_placeid[pid] = {
        'nom': nom, 'nom_norm': nom_norm, 'wilaya': wilaya, 'commune': commune,
        'cat': cat, 'lat': lat, 'lng': lng, 'phone': phone, 'website': website, 'source': source
    }
    key = (nom_norm or '').lower().strip()
    if key:
        prod_by_norm[key].append({
            'place_id': pid, 'nom': nom, 'wilaya': wilaya, 'commune': commune,
            'cat': cat, 'lat': lat, 'lng': lng, 'phone': phone, 'website': website
        })

print("Production: {} places, {} unique place_ids".format(len(prod_rows), len(prod_by_placeid)))

# Load test database
conn_test = sqlite3.connect(TEST_DB)
c_test = conn_test.cursor()
c_test.execute('''
    SELECT place_id, nom, nom_normalized, wilaya, commune, categorie_recherche,
           latitude, longitude, telephone, site_web, source
    FROM places WHERE place_id IS NOT NULL
''')
test_rows = c_test.fetchall()

test_by_placeid = {}
for row in test_rows:
    pid, nom, nom_norm, wilaya, commune, cat, lat, lng, phone, website, source = row
    test_by_placeid[pid] = {
        'place_id': pid,
        'nom': nom, 'nom_norm': nom_norm, 'wilaya': wilaya, 'commune': commune,
        'cat': cat, 'lat': lat, 'lng': lng, 'phone': phone, 'website': website, 'source': source
    }

print("National Test: {} places, {} unique place_ids".format(len(test_rows), len(test_by_placeid)))

# ========== 1. COMPARER PAR PLACE_ID ==========
print("\n" + "=" * 80)
print("1. COMPARAISON PAR PLACE_ID")
print("=" * 80)

prod_ids = set(prod_by_placeid.keys())
test_ids = set(test_by_placeid.keys())

common_ids = prod_ids & test_ids
new_in_test = test_ids - prod_ids
missing_in_test = prod_ids - test_ids  # should be empty

print("place_ids communs: {}".format(len(common_ids)))
print("Nouveaux dans test (absents de prod): {}".format(len(new_in_test)))
print("Dans prod mais pas dans test: {}".format(len(missing_in_test)))

# ========== 2. LISTE DES NOUVEAUX ==========
print("\n" + "=" * 80)
print("2. ETABLISSEMENTS DANS TEST MAIS ABSENTS DE PRODUCTION")
print("=" * 80)

new_entries = []
for pid in sorted(new_in_test):
    entry = test_by_placeid[pid]
    new_entries.append(entry)
    print("  place_id={} | {} | {} | {} | {} | GPS=({}, {}) | source={}".format(
        pid, safe(entry['nom'][:60]), safe(entry['wilaya']), safe(entry['commune'] or '-'),
        safe(entry['cat']), entry['lat'], entry['lng'], safe(entry['source'])))

# ========== 3. UNICITE METIER ==========
print("\n" + "=" * 80)
print("3. VERIFICATION UNICITE METIER (nom normalise + wilaya + categorie)")
print("=" * 80)

business_duplicates = []
for entry in new_entries:
    nom_norm = (entry['nom_norm'] or '').lower().strip()
    wilaya = entry['wilaya']
    cat = entry['cat']
    
    # Check against production
    matches = []
    for prod_entry in prod_by_norm.get(nom_norm, []):
        if prod_entry['wilaya'] == wilaya and prod_entry['cat'] == cat:
            matches.append(prod_entry)
    
    # Also check fuzzy match (significant word overlap)
    if not matches:
        nom_words = set(nom_norm.split())
        for key, prod_list in prod_by_norm.items():
            key_words = set(key.split())
            overlap = len([w for w in nom_words & key_words if len(w) > 3])
            if overlap >= 2:
                for pe in prod_list:
                    if pe['wilaya'] == wilaya and pe['cat'] == cat:
                        matches.append(pe)
    
    if matches:
        business_duplicates.append({
            'test_entry': entry,
            'matches': matches
        })
        print("  DOUBLON METIER PROBABLE:")
        print("    Test: place_id={} | {} | {} | {} | GPS=({}, {})".format(
            entry['place_id'], safe(entry['nom'][:50]), wilaya, cat, entry['lat'], entry['lng']))
        for m in matches[:3]:
            print("    Prod: place_id={} | {} | {} | GPS=({}, {})".format(
                m['place_id'], safe(m['nom'][:50]), m['wilaya'], m['lat'], m['lng']))

print("\nTotal doublons metier probables: {}".format(len(business_duplicates)))

# ========== 4. REPARTITION PAR WILAYA/COMMUNE/CATEGORIE ==========
print("\n" + "=" * 80)
print("4. REPARTITION DES NOUVELLES ENTREES")
print("=" * 80)

wilaya_stats = defaultdict(int)
commune_stats = defaultdict(int)
cat_stats = defaultdict(int)
missing_commune = 0
missing_coords = 0

for entry in new_entries:
    wilaya_stats[entry['wilaya']] += 1
    if entry['commune'] and entry['commune'].strip():
        commune_stats[entry['commune']] += 1
    else:
        missing_commune += 1
    cat_stats[entry['cat']] += 1
    if entry['lat'] is None or entry['lng'] is None:
        missing_coords += 1

print("\nPar wilaya:")
for w, c in sorted(wilaya_stats.items(), key=lambda x: -x[1]):
    print("  {}: {}".format(w, c))

print("\nPar categorie:")
for cat, c in sorted(cat_stats.items(), key=lambda x: -x[1]):
    print("  {}: {}".format(cat, c))

print("\nCommunes manquantes: {}".format(missing_commune))
print("Coordonnées manquantes: {}".format(missing_coords))

# Top communes
print("\nTop 20 communes:")
for comm, c in sorted(commune_stats.items(), key=lambda x: -x[1])[:20]:
    print("  {}: {}".format(comm, c))

# ========== 5. CONTROLE GPS ==========
print("\n" + "=" * 80)
print("5. CONTROLE DES COORDONNEES GPS")
print("=" * 80)

gps_issues = {
    'null': [],
    'out_of_bounds': [],
    'duplicate_coords': defaultdict(list),
    'suspicious_precision': []
}

coord_counts = defaultdict(list)
for entry in new_entries:
    lat, lng = entry['lat'], entry['lng']
    pid = entry['place_id']
    
    if lat is None or lng is None:
        gps_issues['null'].append(entry)
        continue
    
    # Check bounds
    if not (ALGERIA_BOUNDS['lat_min'] <= lat <= ALGERIA_BOUNDS['lat_max'] and
            ALGERIA_BOUNDS['lng_min'] <= lng <= ALGERIA_BOUNDS['lng_max']):
        gps_issues['out_of_bounds'].append(entry)
    
    # Track duplicates
    coord_key = (round(lat, 6), round(lng, 6))
    coord_counts[coord_key].append(entry)

# Find duplicate coordinates
for coord, entries in coord_counts.items():
    if len(entries) > 1:
        gps_issues['duplicate_coords'][coord] = entries

print("Coordonnées nulles: {}".format(len(gps_issues['null'])))
print("Hors limites Algerie: {}".format(len(gps_issues['out_of_bounds'])))
print("Coordonnées dupliquees (meme lat/lng arrondi): {}".format(len(gps_issues['duplicate_coords'])))

if gps_issues['duplicate_coords']:
    print("\nCoordonnées identiques anormales:")
    for coord, entries in gps_issues['duplicate_coords'].items():
        print("  GPS {}: {} entrees".format(coord, len(entries)))
        for e in entries[:5]:
            print("    - place_id={} | {} | {} | {}".format(e['place_id'], safe(e['nom'][:40]), safe(e['wilaya']), safe(e['cat'])))

if gps_issues['out_of_bounds']:
    print("\nHors limites:")
    for e in gps_issues['out_of_bounds'][:10]:
        print("  place_id={} | {} | GPS=({}, {})".format(e['place_id'], safe(e['nom'][:40]), e['lat'], e['lng']))

# ========== 6. TELEPHONES, ADRESSES, SITES WEB ==========
print("\n" + "=" * 80)
print("6. CONTROLE TELEPHONES, ADRESSES, SITES WEB")
print("=" * 80)

phone_stats = {'present': 0, 'missing': 0, 'suspicious': []}
website_stats = {'present': 0, 'missing': 0, 'suspicious': []}

suspicious_phones = defaultdict(int)
suspicious_websites = defaultdict(int)

for entry in new_entries:
    phone = entry['phone']
    website = entry['website']
    
    if phone and phone.strip():
        phone_stats['present'] += 1
        suspicious_phones[phone] += 1
    else:
        phone_stats['missing'] += 1
    
    if website and website.strip():
        website_stats['present'] += 1
        suspicious_websites[website] += 1
    else:
        website_stats['missing'] += 1

print("Telephones: presents={}, manquants={}".format(phone_stats['present'], phone_stats['missing']))
print("Sites web: presents={}, manquants={}".format(website_stats['present'], website_stats['missing']))

# Check for repeated phones/websites
repeated_phones = {p: c for p, c in suspicious_phones.items() if c > 1}
repeated_websites = {w: c for w, c in suspicious_websites.items() if c > 1}

if repeated_phones:
    print("\nTelephones repetes (suspects):")
    for p, c in sorted(repeated_phones.items(), key=lambda x: -x[1])[:10]:
        print("  {}: {} fois".format(p, c))

if repeated_websites:
    print("\nSites web repetes (suspects):")
    for w, c in sorted(repeated_websites.items(), key=lambda x: -x[1])[:10]:
        print("  {}: {} fois".format(w, c))

# Check for CDN/template domains
blocked_domains = ['fonts.gstatic.com', 'fonts.googleapis.com', 'gstatic.com',
                   'googleapis.com', 'cloudflare.com', 'bootstrapcdn.com',
                   'jquery.com', 'cdnjs.cloudflare.com']
cdn_websites = []
for entry in new_entries:
    if entry['website']:
        wl = entry['website'].lower()
        for b in blocked_domains:
            if b in wl:
                cdn_websites.append(entry)
                break

if cdn_websites:
    print("\nSites web CDN/templates detectes: {}".format(len(cdn_websites)))
    for e in cdn_websites[:10]:
        print("  place_id={} | {} | {}".format(e['place_id'], safe(e['nom'][:40]), e['website']))

# ========== 7. JOURNAUX D'IMPORT ==========
print("\n" + "=" * 80)
print("7. ANALYSE DES JOURNAUX D'IMPORT")
print("=" * 80)

import csv
from collections import Counter

log_file = r'C:\SANTE_DZ_SCRAPER\phase6_national_import_log.csv'
actions = Counter()
geo_ids_in_log = set()

with open(log_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        actions[row['action']] += 1
        geo_ids_in_log.add(row['geo_id'])

print("Actions dans le journal:")
for action, count in sorted(actions.items(), key=lambda x: -x[1]):
    print("  {}: {}".format(action, count))

print("\nGeoIDs uniques traites: {}".format(len(geo_ids_in_log)))

# Cross-reference with new entries
imported_placeids = set()
for pid in new_in_test:
    if test_by_placeid[pid]['source'].startswith('geoalgeria'):
        imported_placeids.add(pid)

print("place_ids GeoAlgeria dans test DB: {}".format(len(imported_placeids)))

# ========== 8. BILAN CHIFFRE ==========
print("\n" + "=" * 80)
print("8. BILAN CHIFFRE FINAL")
print("=" * 80)

# Count truly new (not business duplicates)
truly_new = len(new_entries) - len(business_duplicates)
probable_duplicates = len(business_duplicates)
rejected_no_gps = len(gps_issues['null'])
out_of_bounds = len(gps_issues['out_of_bounds'])
coord_duplicates = sum(len(v) - 1 for v in gps_issues['duplicate_coords'].values())
reliable_for_integration = truly_new - rejected_no_gps - out_of_bounds - coord_duplicates

print("Entrees GeoAlgeria dans test DB: {}".format(len(new_entries)))
print("  - Nouvelles (place_id absent de prod): {}".format(len(new_entries)))
print("  - Doublons metier probables (nom+wilaya+cat): {}".format(probable_duplicates))
print("  - Vraiment nouvelles apres dedup metier: {}".format(truly_new))
print("  - Sans coordonnees GPS: {}".format(rejected_no_gps))
print("  - Hors limites Algerie: {}".format(out_of_bounds))
print("  - Coordonnees dupliquees (exces): {}".format(coord_duplicates))
print("  - Fiables pour integration future: {}".format(max(0, reliable_for_integration)))

print("\nPar source:")
source_counts = Counter(e['source'] for e in new_entries)
for s, c in source_counts.most_common():
    print("  {}: {}".format(s, c))

# Precision/Method breakdown for geoalgeria entries
geo_entries = [e for e in new_entries if e['source'].startswith('geoalgeria')]
print("\nGeoAlgeria - Precision:")
prec_counts = Counter()
method_counts = Counter()
for e in geo_entries:
    # Would need to join with original CSV for precision/method
    pass

conn_prod.close()
conn_test.close()

print("\n" + "=" * 80)
print("FIN DE L'AUDIT")
print("=" * 80)