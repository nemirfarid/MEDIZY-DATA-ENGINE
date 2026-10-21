import csv
import sqlite3

def safe(s):
    if s is None: return ''
    return str(s).encode('ascii','replace').decode()

# Mission 1 - Abadla complete analysis
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db')
c = conn.cursor()

abadla_list = ['053be2b97429a342', '90832d666a6d2057', '679da9f6d5cbfa3f']
print("=== MISSION 1: ANALYSE COMPLETE ABADLA ===\n")
for pid in abadla_list:
    c.execute('SELECT place_id, nom, nom_normalized, wilaya, commune, categorie_recherche, latitude, longitude, source, created_at FROM places WHERE place_id=?', (pid,))
    r = c.fetchone()
    if r:
        print(f"place_id: {r[0]}")
        print(f"  nom: {r[1]}")
        print(f"  nom_normalized: {r[2]}")
        print(f"  wilaya/commune: {r[3]}/{r[4]}")
        print(f"  categorie: {r[5]}")
        print(f"  GPS: ({r[6]}, {r[7]})")
        print(f"  source: {r[8]}")
        print(f"  created_at: {r[9]}")
    print()

conn.close()
print("\nANALYSE:")
print("1. geo_id 08-eph-02 apparaît 2 fois (Abadla EPH) avec même geo_id - indique doublon source")
print("2. Entrée 90832d666a6d2057 a nom arabe corrompu (????) dans DB - probablement erreur d'encodage lors import")
print("3. Même GPS, même commune, même catégorie (EPH) entre 053be2b97429a342 et 90832d666a6d2057")
print("4. 679da9f6d5cbfa3f est EPSP distinct (même GPS mais catégorie différente - co-localisation valide)\n")
print("CONCLUSION: 053be2b97429a342 et 90832d666a6d2057 sont un doublon source (même geo_id 08-eph-02).")
print("Ne pas fusionner/supprimer - documenter comme doublon probable de source à confirmer.")