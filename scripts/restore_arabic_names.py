import sqlite3
import pandas as pd
import urllib.parse
import re

print("Restauration des noms arabes originaux depuis les URLs Google Maps...")

df = pd.read_csv(r'C:\Users\pc lenovo\Downloads\Google Maps Extractor\all-task-1-overview.csv')

# Créer un mapping place_id ou lien -> nom arabe réel
url_to_arabic = {}
for _, row in df.iterrows():
    name = str(row['name'])
    link = str(row.get('link', ''))
    if not link or link == 'nan':
        continue
    
    # Extraire le nom encodé dans /place/<nom>/
    m = re.search(r'/place/([^/]+)/', link)
    if m:
        decoded_name = urllib.parse.unquote_plus(m.group(1))
        # Vérifier si contient des caractères arabes
        if any('\u0600' <= char <= '\u06FF' for char in decoded_name):
            url_to_arabic[name] = decoded_name

print(f"Trouvé {len(url_to_arabic)} correspondances avec noms arabes authentiques.")

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

updated_count = 0
for garbled, real_arabic in url_to_arabic.items():
    c.execute("UPDATE facilities SET nom = ? WHERE nom = ?", (real_arabic, garbled))
    updated_count += c.rowcount

conn.commit()
print(f"Nombre de fiches mises à jour avec leur nom arabe exact : {updated_count}")

# Vérifier s'il reste des noms contenant des translitérations Buckwalter évidentes
c.execute("SELECT count(*) FROM facilities WHERE nom LIKE '%@%' OR nom LIKE '%aayd%'")
remaining = c.fetchone()[0]
print(f"Reste avec caractères anormaux : {remaining}")

conn.close()

