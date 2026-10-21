import sqlite3
import csv
import re

def build_nom_normalized(name_fr: str) -> str:
    n = name_fr.lower().strip()
    for prefix in ['établissement public hospitalier', 'etablissement public hospitalier',
                   'hôpital', 'hopital', 'centre de santé', 'centre de sante',
                   'clinique', 'institut', 'epsp', 'eph', 'eh', 'ehs', 'ehu']:
        n = n.replace(prefix, '').strip()
    n = n.replace('(', '').replace(')', '').strip()
    n = re.sub(r'\s+', ' ', n)
    return n

MIPH_TYPE_TO_CATEGORIE = {
    'CHU': 'hôpital', 'EPH': 'hôpital', 'EH': 'hôpital', 'EHS': 'clinique',
    'EHU': 'hôpital', 'EPSP': 'centre de santé', 'DSP': 'Structure',
    'INSTITUT/FORMATION': 'Institut de formation', 'EST': 'Institut de formation',
    'INFSPM': 'Institut de formation', 'INFPM': 'Institut de formation',
    'IFPM': 'Institut de formation', 'IFSM': 'Institut de formation',
    'DRH': 'Direction', 'Structure': 'Structure',
}

# Load MIPH CSV
with open(r'D:\SANTE_DZ_EXPORTS\miph_crossref_new.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    csv_rows = list(reader)

# Check for duplicates WITHIN the CSV (same nom_normalized + wilaya + categorie)
print("=" * 100)
print("VÉRIFICATION DOUBLONS MÉTIER AU SEIN DU CSV MIPH")
print("=" * 100)

csv_entities = []
for r in csv_rows:
    name_fr = r['etab_fr'].strip()
    wilaya = r['wilaya'].strip()
    type_etab = r['type_etab'].strip()
    categorie = MIPH_TYPE_TO_CATEGORIE.get(type_etab, 'Structure')
    nom_norm = build_nom_normalized(name_fr)
    csv_entities.append({
        'pdf_id': r['pdf_id'],
        'nom': name_fr,
        'wilaya': wilaya,
        'categorie': categorie,
        'nom_normalized': nom_norm,
        'postal_code': r['code_postal'].strip(),
    })

# Check within CSV
seen = {}
for e in csv_entities:
    key = (e['nom_normalized'], e['wilaya'].lower(), e['categorie'])
    if key in seen:
        print(f"WARNING DOUBLON METIER DANS CSV: {e['pdf_id']} vs {seen[key]['pdf_id']}")
        print(f"    Nom: {e['nom']} | {seen[key]['nom']}")
        print(f"    Wilaya: {e['wilaya']} | Catégorie: {e['categorie']}")
        print(f"    Nom normalized: {e['nom_normalized']}")
    else:
        seen[key] = e

print(f"\nClés uniques (nom_normalized + wilaya + categorie): {len(seen)} / {len(csv_entities)}")
if len(seen) == len(csv_entities):
    print("OK AUCUN doublon métier au sein du CSV MIPH")

# Check against production DB for potential false business duplicates
print("\n" + "=" * 100)
print("VÉRIFICATION DOUBLONS MÉTIER MIPH CSV vs BASE PRODUCTION (hors place_id)")
print("=" * 100)

prod = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = prod.cursor()

# Get all existing places with their normalized names
c.execute("""
    SELECT id, nom, nom_normalized, wilaya_normalized, categorie_recherche, source, latitude, longitude
    FROM places
""")
all_places = c.fetchall()

# Build lookup
db_lookup = {}
for p in all_places:
    db_id, nom, nom_norm, wilaya_norm, cat, source, lat, lon = p
    key = (nom_norm, wilaya_norm, cat)
    if key not in db_lookup:
        db_lookup[key] = []
    db_lookup[key].append({
        'id': db_id, 'nom': nom, 'source': source, 'lat': lat, 'lon': lon
    })

# Check each MIPH entity against DB
false_positives = []
for e in csv_entities:
    key = (e['nom_normalized'], e['wilaya'].lower(), e['categorie'])
    if key in db_lookup:
        matches = db_lookup[key]
        # Check if match is the SAME entity (by place_id)
        place_id = f"miph_{e['pdf_id']}"
        c.execute('SELECT id FROM places WHERE place_id = ?', (place_id,))
        exact_match = c.fetchone()
        
        for m in matches:
            if m['id'] == exact_match[0]:
                # This is the correct match - same entity
                continue
            else:
                # Potential FALSE POSITIVE - different entity with same nom_norm + wilaya + cat
                false_positives.append({
                    'miph_pdf_id': e['pdf_id'],
                    'miph_nom': e['nom'],
                    'miph_wilaya': e['wilaya'],
                    'miph_categorie': e['categorie'],
                    'miph_nom_norm': e['nom_normalized'],
                    'db_id': m['id'],
                    'db_nom': m['nom'],
                    'db_source': m['source'],
                    'db_lat': m['lat'],
                    'db_lon': m['lon'],
                })

if false_positives:
    print(f"WARNING {len(false_positives)} FAUX DOUBLONS MÉTIER DÉTECTÉS (différentes entités, même clé métier):")
    for fp in false_positives:
        print(f"  MIPH pdf_id={fp['miph_pdf_id']}: {fp['miph_nom']} [{fp['miph_wilaya']}/{fp['miph_categorie']}]")
        print(f"    -> DB id={fp['db_id']}: {fp['db_nom']} [source={fp['db_source']}, GPS=({fp['db_lat']},{fp['db_lon']})]")
        print(f"    Clé métier: nom_norm='{fp['miph_nom_norm']}', wilaya='{fp['miph_wilaya'].lower()}', cat='{fp['miph_categorie']}'")
else:
    print("OK AUCUN faux doublon métier détecté entre CSV MIPH et base production")
    print("   (tous les matchs par nom_normalized+wilaya+categorie correspondent aux mêmes entités par place_id)")

# Also check: are there DB entries with same nom_normalized but DIFFERENT wilaya or category?
# This would be legitimate distinct establishments
print("\n" + "=" * 100)
print("ENTITÉS AVEC MÊME NOM NORMALIZED MAIS WILAYA/CATÉGORIE DIFFÉRENTES (légitimes)")
print("=" * 100)

nom_groups = {}
for p in all_places:
    db_id, nom, nom_norm, wilaya_norm, cat, source, lat, lon = p
    if nom_norm not in nom_groups:
        nom_groups[nom_norm] = []
    nom_groups[nom_norm].append({
        'id': db_id, 'nom': nom, 'wilaya': wilaya_norm, 'cat': cat, 'source': source
    })

for nom_norm, group in nom_groups.items():
    if len(group) > 1:
        wilayas = set(g['wilaya'] for g in group)
        cats = set(g['cat'] for g in group)
        if len(wilayas) > 1 or len(cats) > 1:
            print(f"  Nom normalized: '{nom_norm}' ({len(group)} occurrences)")
            for g in group:
                print(f"    id={g['id']}, wilaya={g['wilaya']}, cat={g['cat']}, source={g['source']}, nom={g['nom']}")

prod.close()