import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Categories to blacklist completely (clearly non-health commercial/leisure/government/restaurant)
blacklist_words = [
    'restaurant', 'hotel', 'spa', 'sauna', 'supermarche', 'epicerie', 'manucure', 
    'fitness', 'auto', 'voyage', 'banque', 'assurance', 'avocat', 'notaire', 
    'immobilier', 'construction', 'ecole', 'universite', 'faculte', 'parking', 
    'plage', 'parc', 'police', 'pateesire', 'patisserie', 'boulangerie', 'cafe', 
    'barbier', 'coiffure', 'cinema', 'musee', 'stade', 'zoo', 'theatre',
    'garage', 'station', 'electricien', 'serrurier', 'traiteur', 'usine', 'lingerie',
    'vetement', 'chaussure', 'bijouterie', 'boucherie', 'poissonnerie', 'meuble'
]

# We only delete if neither nom nor categorie indicates medical/doctor/pharmacy/hopital/clinique
query_del = """
DELETE FROM facilities
WHERE (
    lower(categorie) LIKE '%restaurant%' OR lower(categorie) LIKE '%supermarche%' OR lower(categorie) LIKE '%hotel%'
    OR lower(categorie) LIKE '%salon de manucure%' OR lower(categorie) LIKE '%salle de fitness%' OR lower(categorie) LIKE '%sauna%'
    OR lower(categorie) LIKE '%universite%' OR lower(categorie) LIKE '%faculte%' OR lower(categorie) LIKE '%ecole%'
    OR lower(categorie) LIKE '%parking%' OR lower(categorie) LIKE '%garage%' OR lower(categorie) LIKE '%patisserie%'
    OR lower(categorie) LIKE '%station thermale%' OR lower(categorie) LIKE '%lotissement%' OR lower(categorie) LIKE '%residence%'
    OR lower(categorie) LIKE '%tresor public%' OR lower(categorie) LIKE '%police%' OR lower(categorie) LIKE '%banque%'
    OR lower(categorie) LIKE '%assurance%' OR lower(categorie) LIKE '%avocat%' OR lower(categorie) LIKE '%siege social%'
    OR lower(categorie) LIKE '%administration%' OR lower(categorie) LIKE '%centre de formation%'
)
AND NOT (
    lower(nom) LIKE '%dr%' OR lower(nom) LIKE '%docteur%' OR lower(nom) LIKE '%médecin%' OR lower(nom) LIKE '%medecin%'
    OR lower(nom) LIKE '%clinique%' OR lower(nom) LIKE '%hopital%' OR lower(nom) LIKE '%hôpital%' OR lower(nom) LIKE '%pharmacie%'
    OR lower(nom) LIKE '%laboratoire%' OR lower(nom) LIKE '%cabinet%' OR lower(nom) LIKE '%dent%' OR lower(nom) LIKE '%centre médical%'
    OR lower(nom) LIKE '%centre medical%' OR lower(nom) LIKE '%epsp%' OR lower(nom) LIKE '%eph%' OR lower(nom) LIKE '%chu%'
)
"""

c.execute(query_del)
print(f"Deleted non-health establishments: {c.rowcount}")

c.execute("DELETE FROM facilities_rtree")
c.execute("INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon) SELECT id, latitude, latitude, longitude, longitude FROM facilities")
print("Remaining genuine health facilities:", c.execute("SELECT count(1) FROM facilities").fetchone()[0])

conn.commit()
conn.close()

