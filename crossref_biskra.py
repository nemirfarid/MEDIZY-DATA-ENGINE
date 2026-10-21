import sqlite3
import csv

# Load GeoAlgeria Biskra entries
with open(r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    geo_rows = [r for r in reader if r['wilaya_code'] == '07']

print("GeoAlgeria Biskra entries: {}".format(len(geo_rows)))

# Connect to production DB
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Get all Biskra establishments from our DB
c.execute('''
    SELECT id, nom, nom_normalized, wilaya, commune, categorie_recherche, latitude, longitude, source
    FROM places 
    WHERE wilaya = "Biskra" OR wilaya_normalized = "biskra"
''')
db_rows = c.fetchall()
print("Current DB Biskra entries: {}".format(len(db_rows)))

# Build lookup from DB by normalized name
db_by_name = {}
for row in db_rows:
    db_id, nom, nom_norm, wilaya, commune, cat, lat, lon, source = row
    key = nom_norm.lower().strip() if nom_norm else ''
    if key:
        if key not in db_by_name:
            db_by_name[key] = []
        db_by_name[key].append({
            'id': db_id, 'nom': nom, 'wilaya': wilaya, 'commune': commune,
            'cat': cat, 'lat': lat, 'lon': lon, 'source': source
        })

# Cross-reference
print("\n" + "=" * 80)
print("CROSS-REFERENCE: GeoAlgeria Biskra vs Current DB")
print("=" * 80)

new_candidates = []
matches = []
for geo in geo_rows:
    geo_name = geo['name_fr'] or geo['name'] or ''
    geo_name_norm = geo_name.lower().strip()
    # Clean like our normalization
    for prefix in ['etablissement public hospitalier', 'hopital', 'centre de sante',
                   'clinique', 'institut', 'epsp', 'eph', 'eh', 'ehs', 'ehu']:
        geo_name_norm = geo_name_norm.replace(prefix, '').strip()
    geo_name_norm = geo_name_norm.replace('(', '').replace(')', '').strip()
    geo_name_norm = ' '.join(geo_name_norm.split())
    
    geo_commune = geo['commune'] or ''
    geo_type = geo['type']
    geo_lat = float(geo['lat']) if geo['lat'] else None
    geo_lng = float(geo['lng']) if geo['lng'] else None
    
    # Try to find match - better matching using key words
    found = False
    for key, matches_list in db_by_name.items():
        # Check if names are similar (substring or high overlap)
        geo_words = set(geo_name_norm.split())
        db_words = set(key.split())
        overlap = len(geo_words & db_words)
        # Require at least 2 significant words in common
        significant_overlap = len([w for w in geo_words & db_words if len(w) > 3])
        if significant_overlap >= 2 or (geo_name_norm and geo_name_norm in key) or (key and key in geo_name_norm):
            for m in matches_list:
                matches.append({
                    'geo_id': geo['id'],
                    'geo_name': geo_name,
                    'geo_type': geo_type,
                    'geo_commune': geo_commune,
                    'geo_lat': geo_lat,
                    'geo_lng': geo_lng,
                    'db_id': m['id'],
                    'db_name': m['nom'],
                    'db_commune': m['commune'],
                    'db_cat': m['cat'],
                    'db_source': m['source']
                })
                found = True
    
    if not found:
        new_candidates.append({
            'geo_id': geo['id'],
            'geo_name': geo_name,
            'geo_name_ar': geo['name_ar'] or '',
            'geo_type': geo_type,
            'geo_type_label_fr': geo['type_label_fr'],
            'geo_commune': geo_commune,
            'geo_commune_code': geo['commune_code'],
            'geo_lat': geo_lat,
            'geo_lng': geo_lng,
            'geo_precision': geo['geo_precision'],
            'geo_method': geo['geo_method'],
            'geo_source': geo['source'],
            'geo_refs': geo['refs']
        })

print("\nMATCHES (already in DB): {}".format(len(matches)))
for m in matches:
    # ASCII-safe output
    geo_name = m['geo_name'].encode('ascii', 'replace').decode()
    db_name = m['db_name'].encode('ascii', 'replace').decode()
    geo_commune = m['geo_commune'].encode('ascii', 'replace').decode()
    db_commune = m['db_commune'].encode('ascii', 'replace').decode()
    print("  Geo: {} - {} ({})".format(m['geo_id'], geo_name, geo_commune))
    print("  DB:  id={} - {} ({}) [{}]".format(m['db_id'], db_name, db_commune, m['db_cat']))

print("\nNEW CANDIDATES (not in DB): {}".format(len(new_candidates)))
for nc in new_candidates:
    geo_name = nc['geo_name'].encode('ascii', 'replace').decode()
    geo_commune = nc['geo_commune'].encode('ascii', 'replace').decode()
    lat_str = "{:.6f}".format(nc['geo_lat']) if nc['geo_lat'] else "NULL"
    lng_str = "{:.6f}".format(nc['geo_lng']) if nc['geo_lng'] else "NULL"
    print("  {}: {} | type={} ({}) | commune={} | GPS=({}, {}) | precision={} | method={}".format(
        nc['geo_id'], geo_name, nc['geo_type'], nc['geo_type_label_fr'], 
        geo_commune, lat_str, lng_str, nc['geo_precision'], nc['geo_method']))

conn.close()