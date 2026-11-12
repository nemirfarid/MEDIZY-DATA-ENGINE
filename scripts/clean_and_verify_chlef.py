import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Categories to remove (non-medical / noise)
NON_HEALTH = [
    'Magasin de produits de beaute', 'Magasin de meubles', 'Magasin de vetements',
    'Fabricant de produits en ceramique', 'Centre de loisirs', 'Code postal',
    'nan', 'Centre d\'information', 'Etablissement d\'enseignement professionnel',
    'Entreprise de cosmetique'
]

for nh in NON_HEALTH:
    c.execute("DELETE FROM facilities WHERE wilaya_code = '02' AND (categorie = ? OR categorie IS NULL)", (nh,))
    print(f"Deleted {c.rowcount} entries with category '{nh}'")

# Map of raw Google Maps category tags to clean canonical categories
CLEAN_MAPPING = {
    'Cabinet medical': 'Médecin',
    'Cabinet Médical': 'Médecin',
    'Medecin': 'Médecin',
    'Medecin generaliste': 'Médecin Généraliste',
    'Interniste': 'Médecine Interne',
    'Medecin specialiste de la douleur': 'Médecin',
    'Medecin specialiste de la gestion de la douleur': 'Médecin',
    'Medecin specialiste de la fertilite': 'Gynécologue',
    'Gynecologue-obstetricien': 'Gynécologue',
    'Maison de naissance': 'Maternité / Gynécologue',
    'Cabinet dentaire': 'Dentiste',
    'Chirurgie Dentaire': 'Dentiste',
    'Hopital': 'Hôpital & Urgences',
    'Hôpital': 'Hôpital & Urgences',
    'Hopital prive': 'Clinique Privée',
    'Hopital psychiatrique': 'Hôpital Spécialisé',
    'Service hospitalier': 'Hôpital & Urgences',
    'Clinique Médicale': 'Clinique',
    'Hôpital & Clinique': 'Clinique',
    'Clinique chirurgicale': 'Clinique Chirurgicale',
    'Clinique accessible sans rendez-vous': 'Clinique / Urgences',
    'Laboratoire d\'analyse medicale': 'Laboratoire d\'Analyses',
    'Laboratoire': 'Laboratoire d\'Analyses',
    'Centre d\'imagerie pour diagnostic medical': 'Centre d\'Imagerie & Radiologie',
    'Imagerie / Radio': 'Centre d\'Imagerie & Radiologie',
    'Service de mammographie': 'Centre d\'Imagerie & Radiologie',
    'Pediatre': 'Pédiatre',
    'Pédiatre': 'Pédiatre',
    'Ophtalmologiste': 'Ophtalmologue',
    'Kinesitherapeute': 'Kinésithérapeute',
    'Dispensaire': 'Polyclinique / Dispensaire',
    'Centre de sante communautaire': 'Polyclinique / Dispensaire',
    'Centre medical': 'Centre Médical',
    'Centre medical public': 'Centre de Santé Public',
    'Maison de sante': 'Centre de Santé',
    'Groupe medical': 'Centre Médical',
    'Centre de soins ambulatoires': 'Centre de Santé',
    'Pharmacie bio': 'Pharmacie',
    'Drugstore': 'Pharmacie',
    'Parapharmacie': 'Parapharmacie',
    'Conseiller sante': 'Professionnel de Santé',
    'Service de la sante au travail': 'Santé au Travail',
    'Service de sante mentale': 'Santé Mentale',
    'Centre de reeducation': 'Centre de Rééducation',
    'Fournisseur d\'equipements medicaux': 'Matériel Médical',
    'Magasin de materiel medical': 'Matériel Médical',
    'Praticien de medecine alternative': 'Médecine Alternative',
    'Departement de sante publique': 'Structure de Santé Publique',
    'Service de depistage des drogues': 'Laboratoire / Dépistage',
    'Centre de planning familial': 'Centre de Santé',
    'Institut de formation en soins infirmiers': 'Formation Paramédicale',
    'Mutuelle de sante': 'Organisme de Santé'
}

for raw_cat, clean_cat in CLEAN_MAPPING.items():
    c.execute("UPDATE facilities SET categorie = ? WHERE wilaya_code = '02' AND categorie = ?", (clean_cat, raw_cat))

conn.commit()

# Check bounds (no maritime / extreme coordinates)
c.execute("SELECT id, nom, latitude, longitude FROM facilities WHERE wilaya_code = '02' AND (latitude > 36.65 OR latitude < 35.80 OR longitude < 0.80 OR longitude > 1.90)")
out_of_bounds = c.fetchall()
print(f"Coordinates outside Chlef geographical bounds: {len(out_of_bounds)}")
for o in out_of_bounds:
    print("Out of bound entry:", o)

# Count remaining valid facilities
c.execute("SELECT categorie, COUNT(*) FROM facilities WHERE wilaya_code = '02' GROUP BY categorie ORDER BY COUNT(*) DESC")
print("\n--- STANDARDIZED HEALTH CATEGORIES IN WILAYA 02 (CHLEF) ---")
total = 0
for cat, cnt in c.fetchall():
    print(f"  {cat}: {cnt}")
    total += cnt
print(f"Total valid health structures in Chlef: {total}")

c.execute("INSERT INTO facilities_fts(facilities_fts) VALUES('rebuild')")
conn.commit()

