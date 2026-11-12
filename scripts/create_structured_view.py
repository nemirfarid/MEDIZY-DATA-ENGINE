import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# 1. Create a clean structured view 'v_health_directory' with exact column ordering requested:
# Wilaya, Commune, Catégorie, Coordonnées GPS (Latitude, Longitude), Nom/Établissement, Téléphone, Adresse...
c.execute("DROP VIEW IF EXISTS v_health_directory")
c.execute("""
CREATE VIEW v_health_directory AS
SELECT 
    wilaya_code AS code_wilaya,
    wilaya AS nom_wilaya,
    commune AS nom_commune,
    categorie AS categorie_sante,
    latitude,
    longitude,
    (printf('%.6f, %.6f', latitude, longitude)) AS coordonnees_gps,
    nom AS nom_etablissement_ou_praticien,
    telephone,
    adresse,
    site_web,
    note,
    nombre_avis,
    source
FROM facilities
ORDER BY CAST(wilaya_code AS INTEGER), commune, categorie, nom;
""")

conn.commit()

# Test view
c.execute("SELECT code_wilaya, nom_wilaya, nom_commune, categorie_sante, coordonnees_gps, nom_etablissement_ou_praticien, telephone FROM v_health_directory LIMIT 5")
print("View preview (Top 5 rows):")
for r in c.fetchall():
    print(" ", r)

print("\n--- VIEW v_health_directory CREATED SUCCESSFULLY ---")

