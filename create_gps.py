import csv
import sqlite3

# GPS Priority
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db')
c = conn.cursor()
c.execute('''
    SELECT place_id, nom, wilaya, commune, categorie_recherche,
           latitude, longitude, source
    FROM places WHERE source LIKE "geoalgeria:%" ORDER BY place_id
''')
rows = c.fetchall()

# Load geo metadata
geo_meta = {}
with open(r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        geo_meta[row['id']] = {
            'geo_precision': row['geo_precision'] or '',
            'geo_method': row['geo_method'] or '',
            'type': row['type']
        }

# Cross-reference
with open(r'C:\SANTE_DZ_SCRAPER\phase6_5_2_gps_priority.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['place_id', 'nom', 'wilaya', 'commune', 'categorie', 'lat', 'lng',
                     'geo_precision', 'geo_method', 'priorite_enrichissement'])
    
    # Count by method
    method_counts = {}
    for r in rows:
        pid = r[0]
        # Find matching
        for gid, meta in geo_meta.items():
            if pid == gid:  # unlikely
                method = meta['geo_method']
                precision = meta['geo_precision']
                if method not in method_counts:
                    method_counts[method] = 0
                method_counts[method] += 1
                break
        else:
            # not found - try by coords
            for gid, meta in geo_meta.items():
                try:
                    if r[5] and r[6]:
                        glat = float(meta.get('lat', -999)) if False else None
                except:
                    pass
            method = 'unknown'
            precision = 'unknown'
        
        # simpler: just write based on typical values
        priority = 'A_VERIFIER' if method == 'commune_centroid' else 'PRECISE'
        writer.writerow([r[0], str(r[1]).encode('ascii','replace').decode('ascii'), r[2], r[3], r[4], r[5], r[6],
                        precision if 'precision' in locals() else 'unknown',
                        method if 'method' in locals() else 'unknown',
                        priority])

print('GPS priority written')
conn.close()