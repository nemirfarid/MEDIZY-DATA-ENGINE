import sqlite3
import re
import json

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# 1. Dictionnaire officiel des 58 Wilayas (Code -> Noms normalisés)
WILAYAS_58 = [
    ("01", "Adrar", ["adrar"]),
    ("02", "Chlef", ["chlef", "ech-chlef"]),
    ("03", "Laghouat", ["laghouat"]),
    ("04", "Oum El Bouaghi", ["oum el bouaghi", "oum el-bouaghi"]),
    ("05", "Batna", ["batna"]),
    ("06", "Béjaïa", ["bejaia", "béjaïa", "bougie"]),
    ("07", "Biskra", ["biskra"]),
    ("08", "Béchar", ["bechar", "béchar"]),
    ("09", "Blida", ["blida"]),
    ("10", "Bouira", ["bouira"]),
    ("11", "Tamanrasset", ["tamanrasset", "tamanghasset"]),
    ("12", "Tébessa", ["tebessa", "tébessa"]),
    ("13", "Tlemcen", ["tlemcen"]),
    ("14", "Tiaret", ["tiaret"]),
    ("15", "Tizi Ouzou", ["tizi ouzou", "tizi-ouzou"]),
    ("16", "Alger", ["alger", "algiers", "el djazair"]),
    ("17", "Djelfa", ["djelfa"]),
    ("18", "Jijel", ["jijel"]),
    ("19", "Sétif", ["setif", "sétif"]),
    ("20", "Saïda", ["saida", "saïda"]),
    ("21", "Skikda", ["skikda", "philippeville"]),
    ("22", "Sidi Bel Abbès", ["sidi bel abbes", "sidi bel abbès", "sidi bel-abbes"]),
    ("23", "Annaba", ["annaba", "bône"]),
    ("24", "Guelma", ["guelma"]),
    ("25", "Constantine", ["constantine", "qacentina"]),
    ("26", "Médéa", ["medea", "médéa"]),
    ("27", "Mostaganem", ["mostaganem"]),
    ("28", "M'Sila", ["m'sila", "msila", "m sila"]),
    ("29", "Mascara", ["mascara"]),
    ("30", "Ouargla", ["ouargla"]),
    ("31", "Oran", ["oran", "wahran"]),
    ("32", "El Bayadh", ["el bayadh", "el-bayadh"]),
    ("33", "Illizi", ["illizi"]),
    ("34", "Bordj Bou Arreridj", ["bordj bou arreridj", "bordj bou arréridj", "bba"]),
    ("35", "Boumerdes", ["boumerdes", "boumerdès"]),
    ("36", "El Tarf", ["el tarf", "el-tarf"]),
    ("37", "Tindouf", ["tindouf"]),
    ("38", "Tissemsilt", ["tissemsilt"]),
    ("39", "El Oued", ["el oued", "el-oued", "souf"]),
    ("40", "Khenchela", ["khenchela"]),
    ("41", "Souk Ahras", ["souk ahras", "souk-ahras"]),
    ("42", "Tipaza", ["tipaza", "tipasa"]),
    ("43", "Mila", ["mila"]),
    ("44", "Aïn Defla", ["ain defla", "aïn defla", "ain-defla"]),
    ("45", "Naâma", ["naama", "naâma"]),
    ("46", "Aïn Témouchent", ["ain temouchent", "aïn témouchent"]),
    ("47", "Ghardaïa", ["ghardaia", "ghardaïa"]),
    ("48", "Relizane", ["relizane"]),
    ("49", "El M'Ghair", ["el m'ghair", "el mghair"]),
    ("50", "El Meniaa", ["el meniaa", "el menia"]),
    ("51", "Ouled Djellal", ["ouled djellal"]),
    ("52", "Bordj Badji Mokhtar", ["bordj badji mokhtar"]),
    ("53", "Béni Abbès", ["beni abbes", "béni abbès"]),
    ("54", "Timimoun", ["timimoun"]),
    ("55", "Touggourt", ["touggourt"]),
    ("56", "Djanet", ["djanet"]),
    ("57", "In Salah", ["in salah"]),
    ("58", "In Guezzam", ["in guezzam"])
]

# Remplir wilaya_code pour toutes les wilayas existantes par nom
for code, name, aliases in WILAYAS_58:
    c.execute("UPDATE facilities SET wilaya_code = ?, wilaya = ? WHERE lower(wilaya) = ? OR lower(wilaya) IN ({})".format(
        ','.join('?' * len(aliases))
    ), [code, name, name.lower()] + [a.lower() for a in aliases])

conn.commit()

# Vérifier combien d'entrées ont maintenant un wilaya_code valide
c.execute("SELECT count(*) FROM facilities WHERE wilaya_code != '' AND wilaya_code IS NOT NULL")
print(f"Facilities avec wilaya_code renseigne: {c.fetchone()[0]}")

# 2. Synchroniser les vraies structures OSM de Sidi Ali avec leurs coordonnées métriques réelles
# Charger osm_mostaganem.json
with open('scripts/osm_mostaganem.json', 'r', encoding='utf-8') as f:
    osm_elements = json.load(f)

inserted_osm = 0
for el in osm_elements:
    tags = el.get('tags', {})
    name = tags.get('name', tags.get('name:fr', tags.get('name:ar', '')))
    if not name:
        continue
    lat = el.get('lat') or el.get('center', {}).get('lat')
    lon = el.get('lon') or el.get('center', {}).get('lon')
    if not lat or not lon:
        continue
    
    amenity = tags.get('amenity', '')
    cat = 'Pharmacie' if amenity == 'pharmacy' else ('Hôpital' if amenity == 'hospital' else ('Dentiste' if amenity == 'dentist' else 'Médecin'))
    
    # Vérifier si existe déjà à proximité (< 20 mètres)
    c.execute("SELECT id FROM facilities WHERE abs(latitude - ?) < 0.0002 AND abs(longitude - ?) < 0.0002", (lat, lon))
    exists = c.fetchone()
    if not exists:
        # Insérer la structure réelle
        c.execute("""
            INSERT INTO facilities (nom, categorie, wilaya, wilaya_code, commune, adresse, latitude, longitude, source)
            VALUES (?, ?, 'Mostaganem', '27', 'Sidi Ali', ?, ?, ?, 'OpenStreetMap Verified')
        """, (name, cat, f"{name}, Sidi Ali, Mostaganem", lat, lon))
        new_id = c.lastrowid
        c.execute("INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon) VALUES (?, ?, ?, ?, ?)",
                  (new_id, lat, lat, lon, lon))
        inserted_osm += 1

conn.commit()
print(f"Nouvelles structures réelles OSM insérées à Mostaganem : {inserted_osm}")

# Mettre à jour Pédiatre Dr Ben Tata aux coordonnées exactes OpenStreetMap
c.execute("""
    UPDATE facilities 
    SET latitude = 36.1012142, longitude = 0.4144845, nom = 'Pédiatre Dr Ben Tata', commune = 'Sidi Ali', wilaya = 'Mostaganem', wilaya_code = '27',
        adresse = 'CW 42, Sidi Ali, Mostaganem'
    WHERE nom LIKE '%bentata%' OR nom LIKE '%Ben Tata%'
""")
conn.commit()

# Mettre à jour R-Tree pour Ben Tata
c.execute("SELECT id, latitude, longitude FROM facilities WHERE nom LIKE '%Ben Tata%'")
for r in c.fetchall():
    fid, flat, flon = r
    c.execute("DELETE FROM facilities_rtree WHERE id = ?", (fid,))
    c.execute("INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon) VALUES (?, ?, ?, ?, ?)",
              (fid, flat, flat, flon, flon))
conn.commit()

print("Pédiatre Dr Ben Tata recalibré avec succès !")
conn.close()

