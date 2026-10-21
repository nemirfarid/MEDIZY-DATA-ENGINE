import csv
import sqlite3

def safe_ascii(s):
    if s is None: return ''
    return str(s).encode('ascii','replace').decode('ascii')

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db')
c = conn.cursor()
c.execute("SELECT place_id, nom, wilaya, commune, categorie_recherche, latitude, longitude FROM places WHERE source LIKE 'geoalgeria:%'")
rows = c.fetchall()

geo = {}
with open(r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        geo[row['id']] = {'prec': row['geo_precision'], 'meth': row['geo_method'], 'lat': row['lat'], 'lng': row['lng']}

# Build lookup by coords
with open(r'C:\SANTE_DZ_SCRAPER\phase6_5_2_gps_priority.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['place_id', 'nom', 'wilaya', 'commune', 'categorie', 'lat', 'lng', 'geo_precision', 'geo_method', 'priorite_enrichissement'])
    for r in rows:
        pid = r[0]
        prec = meth = 'unknown'
        priority = 'INCONNU'
        # find best match by coord
        if r[5] and r[6]:
            try:
                rlat = float(r[5])
                rlng = float(r[6])
            except:
                rlat = rlng = None
            if rlat is not None:
                for gid, m in geo.items():
                    try:
                        glat = float(m['lat']) if m['lat'] else None
                        glng = float(m['lng']) if m['lng'] else None
                    except:
                        continue
                    if glat and glng and abs(glat-rlat) < 0.0001 and abs(glng-rlng) < 0.0001:
                        prec = m['prec'] if m['prec'] else 'unknown'
                        meth = m['meth'] if m['meth'] else 'unknown'
                        break
        if meth == 'commune_centroid':
            priority = 'A_VERIFIER_CENTROID'
        elif meth in ('osm_point', 'owner_verified'):
            priority = 'PRECISE'
        else:
            priority = 'A_VERIFIER'
        w.writerow([r[0], safe_ascii(r[1]), r[2], r[3], r[4], r[5], r[6], prec, meth, priority])

print('done')
conn.close()