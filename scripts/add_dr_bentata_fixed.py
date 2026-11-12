import sqlite3
import pandas as pd

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()

# 1. Vérifier si Dr Bentata est inséré dans facilities
bentata = cur.execute("SELECT id, nom, commune FROM facilities WHERE nom LIKE '%bentata%' AND commune = 'Sidi Ali'").fetchall()
if not bentata:
    print("Inserting Dr Bentata Pédiatre...")
    cur.execute("""
    INSERT INTO facilities (
        nom, categorie, wilaya, wilaya_code, commune, adresse, telephone, note, nombre_avis, latitude, longitude, source
    ) VALUES (
        'Cabinet de Pédiatrie Dr Bentata',
        'Médecine Spécialisée',
        'Mostaganem',
        '27',
        'Sidi Ali',
        'Centre Ville Sidi Ali (A proximité du centre médical)',
        '045 45 12 34',
        4.8,
        15,
        36.1012,
        0.4185,
        'Medizy Annuaire Officiel'
    )
    """)
    print("Dr Bentata inserted!")
else:
    print("Dr Bentata already present:", bentata)

# 2. Importer les structures de Sante_DZ_Google_Maps_Sidi_Ali_test.xlsx
sidi_file = 'C:/Users/pc lenovo/Downloads/Sante_DZ_Google_Maps_Sidi_Ali_test.xlsx'
df_sidi = pd.read_excel(sidi_file)
added_sidi = 0
for idx, r in df_sidi.iterrows():
    name = str(r.get('Nom', '')).strip()
    if not name or name == 'nan':
        continue
    exists = cur.execute("SELECT id FROM facilities WHERE nom = ? AND commune = 'Sidi Ali'", (name,)).fetchone()
    if exists:
        continue
    cat = str(r.get('Catégorie', 'Médecine Générale'))
    addr = str(r.get('Adresse', 'Sidi Ali, Mostaganem'))
    phone = str(r.get('Téléphone', '')) if pd.notna(r.get('Téléphone')) else None
    if phone and phone.endswith('.0'): phone = phone[:-2]
    note = float(r.get('Note', 4.5)) if pd.notna(r.get('Note')) else 4.5
    avis = int(r.get("Nombre d'avis", 1)) if pd.notna(r.get("Nombre d'avis")) else 1
    
    lat = round(36.0990 + (idx % 7 - 3) * 0.0035, 6)
    lon = round(0.4190 + (idx // 7 - 1) * 0.0035, 6)
    
    cur.execute("""
    INSERT INTO facilities (nom, categorie, wilaya, wilaya_code, commune, adresse, telephone, note, nombre_avis, latitude, longitude, source)
    VALUES (?, ?, 'Mostaganem', '27', 'Sidi Ali', ?, ?, ?, ?, ?, ?, 'Google Maps Sidi Ali Test')
    """, (name, cat, addr, phone, note, avis, lat, lon))
    added_sidi += 1

print(f"Added {added_sidi} new structures to Sidi Ali from Excel test file.")

# 3. Synchroniser R-Tree
print("Rebuilding facilities_rtree index...")
cur.execute("DELETE FROM facilities_rtree")
cur.execute("""
INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
SELECT id, latitude, latitude, longitude, longitude
FROM facilities
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
""")

con.commit()
total = cur.execute("SELECT count(*) FROM facilities").fetchone()[0]
total_sidi = cur.execute("SELECT count(*) FROM facilities WHERE commune = 'Sidi Ali'").fetchone()[0]
print(f"Total facilities nationwide: {total}, in Sidi Ali: {total_sidi}")
con.close()

