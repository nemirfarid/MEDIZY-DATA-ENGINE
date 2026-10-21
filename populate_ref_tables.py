import sqlite3
from config import WILAYAS, CATEGORIES

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Populate wilayas table
print("Populating wilayas...")
for code, nom_fr in WILAYAS:
    # Try to get lat/lon from places table
    c.execute('SELECT AVG(latitude), AVG(longitude) FROM places WHERE wilaya = ? AND latitude IS NOT NULL AND longitude IS NOT NULL', (nom_fr,))
    avg_lat, avg_lon = c.fetchone()
    c.execute('INSERT OR REPLACE INTO wilayas (code, nom_fr, nom_ar, latitude, longitude) VALUES (?, ?, "", ?, ?)',
              (code, nom_fr, avg_lat, avg_lon))

# Populate categories table
print("Populating categories...")
for i, cat in enumerate(CATEGORIES, 1):
    # Determine general category
    cat_generale = "santé"
    if "dentaire" in cat or "dentiste" in cat:
        cat_generale = "dentaire"
    elif "pharmacie" in cat or "parapharmacie" in cat:
        cat_generale = "pharmacie"
    elif "laboratoire" in cat:
        cat_generale = "laboratoire"
    elif "clinique" in cat or "hôpital" in cat or "polyclinique" in cat:
        cat_generale = "clinique/hôpital"
    elif "médecin" in cat or "cabinet médical" in cat:
        cat_generale = "médecine générale"
    elif "ophtalmologue" in cat or "gynécologue" in cat or "dermatologue" in cat or "cardiologue" in cat or "pédiatre" in cat or "ORL" in cat or "neurologue" in cat or "urologue" in cat or "gastro-entérologue" in cat:
        cat_generale = "spécialités médicales"
    elif "kinésithérapeute" in cat or "kinésithérapie" in cat or "rééducation" in cat:
        cat_generale = "kinésithérapie/rééducation"
    elif "sage-femme" in cat:
        cat_generale = "sage-femme"
    elif "psychologue" in cat or "psychiatre" in cat:
        cat_generale = "psychologie/psychiatrie"
    elif "radiologue" in cat or "imagerie" in cat:
        cat_generale = "radiologie/imagerie"
    elif "nutritionniste" in cat:
        cat_generale = "nutrition"
    elif "orthophoniste" in cat:
        cat_generale = "orthophonie"
    elif "ostéopathe" in cat:
        cat_generale = "ostéopathie"
    elif "vétérinaire" in cat:
        cat_generale = "vétérinaire"
    
    c.execute('INSERT OR REPLACE INTO categories (id, code, nom_fr, categorie_generale, variantes_recherche) VALUES (?, ?, ?, ?, ?)',
              (i, f"CAT{i:03d}", cat, cat_generale, cat))

conn.commit()
print("Wilayas and categories populated")

# Verify
c.execute('SELECT COUNT(*) FROM wilayas')
print(f"Wilayas: {c.fetchone()[0]}")
c.execute('SELECT COUNT(*) FROM categories')
print(f"Categories: {c.fetchone()[0]}")

conn.close()