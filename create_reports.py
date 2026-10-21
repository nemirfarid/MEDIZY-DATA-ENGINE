# Mission 3-5: Create reports properly
import csv
import sqlite3

def safe_ascii(s):
    if s is None: return ''
    return str(s).encode('ascii','replace').decode('ascii')

# Mission 1 details
results = []

# Analyze all 4 non-classified
non_classified = ['298468c8d4dab055', '373a162cb3954ebd', '90832d666a6d2057', '9fd18ce470ce8945']
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db')
c = conn.cursor()

for pid in non_classified:
    c.execute('SELECT place_id, nom, nom_normalized, wilaya, commune, categorie_recherche, latitude, longitude, source, created_at FROM places WHERE place_id=?', (pid,))
    r = c.fetchone()
    if r:
        results.append({
            'place_id': r[0],
            'nom_db': r[1],
            'nom_norm': r[2],
            'wilaya': r[3],
            'commune': r[4],
            'categorie': r[5],
            'lat': r[6],
            'lng': r[7],
            'source': r[8],
            'created_at': r[9]
        })

conn.close()

# Write manual validation CSV
with open(r'C:\SANTE_DZ_SCRAPER\phase6_5_2_manual_validation.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['place_id', 'nom_db', 'nom_norm', 'wilaya', 'commune', 'categorie', 
                     'latitude', 'longitude', 'source', 'created_at', 
                     'champs_vides', 'problemes', 'action_requise', 'niveau_confiance'])
    for r in results:
        problems = []
        champs_vides = []
        if not r['commune'] or not r['commune'].strip():
            champs_vides.append('commune')
        # Check for ????
        nom = r['nom_db']
        if '????' in nom or '??' in nom:
            problems.append('contient ????')
        writer.writerow([
            r['place_id'],
            safe_ascii(r['nom_db']),
            safe_ascii(r['nom_norm']),
            r['wilaya'],
            r['commune'],
            r['categorie'],
            r['lat'], r['lng'],
            r['source'],
            r['created_at'],
            ';'.join(champs_vides) if champs_vides else '',
            ';'.join(problems) if problems else '',
            'VERIFICATION_MANUELLE_TRANSLITTERATION',
            'FAIBLE'
        ])

print('Written manual validation CSV')