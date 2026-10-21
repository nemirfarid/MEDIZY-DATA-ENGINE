import csv
import sqlite3

TEST_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db'
GEO_CSV = r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv'

conn = sqlite3.connect(TEST_DB)
c = conn.cursor()
c.execute("SELECT place_id, nom, wilaya, commune, categorie_recherche, latitude, longitude FROM places WHERE source LIKE 'geoalgeria:%'")
rows = c.fetchall()

geo = {}
with open(GEO_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        geo[row['id']] = {'prec': row['geo_precision'], 'meth': row['geo_method'], 'lat': row['lat'], 'lng': row['lng']}

with open(r'C:\SANTE_DZ_SCRAPER\phase6_6_gps_validation_queue.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['place_id', 'nom', 'wilaya', 'commune', 'categorie', 'lat', 'lng', 'geo_precision', 'geo_method', 'classification_gps', 'priorite', 'motif'])
    for r in rows:
        pid = r[0]
        prec = meth = 'unknown'
        class_gps = 'méthode inconnue'
        priorite = 'HAUTE'
        motif = 'Métadonnées GPS insuffisantes'
        if r[5] and r[6]:
            try:
                rlat, rlng = float(r[5]), float(r[6])
                for gid, m in geo.items():
                    try:
                        glat = float(m.get('lat','')) if m.get('lat') else None
                        glng = float(m.get('lng','')) if m.get('lng') else None
                        if glat and glng and abs(glat-rlat)<0.0001 and abs(glng-rlng)<0.0001:
                            prec = m['prec'] or 'unknown'
                            meth = m['meth'] or 'unknown'
                            break
                    except:
                        continue
            except:
                pass
        if meth == 'commune_centroid':
            class_gps = 'centroïde de commune'
            priorite = 'MOYENNE'
            motif = 'Centroid commune - non position exacte établissement'
        elif meth == 'osm_point':
            class_gps = 'point OSM'
            priorite = 'BASSE'
            motif = 'OSM point - à vérifier si réel'
        elif meth == 'owner_verified':
            class_gps = 'position vérifiée sur terrain (non prouvé)'
            priorite = 'BASSE'
            motif = 'À confirmer'
        w.writerow([pid, str(r[1]).encode('ascii','replace').decode('ascii'), r[2], r[3], r[4], r[5], r[6], prec, meth, class_gps, priorite, motif])

print('done')
conn.close()