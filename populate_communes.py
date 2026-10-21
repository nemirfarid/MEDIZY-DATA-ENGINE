import sqlite3
import json

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Load communes data
with open(r'C:\SANTE_DZ_SCRAPER\communes_algerie_officielles.json', 'r', encoding='utf-8') as f:
    communes_data = json.load(f)

print(f"Loaded {len(communes_data)} commune entries")

# Map wilaya names to codes
wilaya_code_map = {
    "Adrar": "01", "Chlef": "02", "Laghouat": "03", "Oum El Bouaghi": "04", "Batna": "05",
    "Béjaïa": "06", "Biskra": "07", "Béchar": "08", "Blida": "09", "Bouira": "10",
    "Tamanrasset": "11", "Tébessa": "12", "Tlemcen": "13", "Tiaret": "14", "Tizi Ouzou": "15",
    "Alger": "16", "Djelfa": "17", "Jijel": "18", "Sétif": "19", "Saïda": "20", "Skikda": "21",
    "Sidi Bel Abbès": "22", "Annaba": "23", "Guelma": "24", "Constantine": "25", "Médéa": "26",
    "Mostaganem": "27", "M'Sila": "28", "Mascara": "29", "Ouargla": "30", "Oran": "31",
    "El Bayadh": "32", "Illizi": "33", "Bordj Bou Arréridj": "34", "Boumerdès": "35",
    "El Tarf": "36", "Tindouf": "37", "Tissemsilt": "38", "El Oued": "39", "Khenchela": "40",
    "Souk Ahras": "41", "Tipaza": "42", "Mila": "43", "Aïn Defla": "44", "Naâma": "45",
    "Aïn Témouchent": "46", "Ghardaïa": "47", "Relizane": "48", "Timimoun": "49",
    "Bordj Badji Mokhtar": "50", "Ouled Djellal": "51", "Béni Abbès": "52", "In Salah": "53",
    "In Guezzam": "54", "Touggourt": "55", "Djanet": "56", "El M'Ghair": "57", "El Meniaa": "58",
}

# Also need reverse map for English names
wilaya_en_to_fr = {}
for fr, code in wilaya_code_map.items():
    # We'll need to match by English name from the JSON
    pass

# The JSON uses English names for wilayas. Let's build a mapping.
# First, extract unique wilaya names from the data
wilaya_names = set()
for commune in communes_data:
    for ancestor in commune.get('ancestors', []):
        if ancestor.get('level') == 1:
            wilaya_names.add(ancestor['name']['en'])

print(f"Unique wilayas in data: {sorted(wilaya_names)}")

# Map English to French
en_to_fr = {
    "Adrar": "Adrar", "Chlef": "Chlef", "Laghouat": "Laghouat", "Oum El Bouaghi": "Oum El Bouaghi",
    "Batna": "Batna", "Bejaia": "Béjaïa", "Biskra": "Biskra", "Bechar": "Béchar",
    "Blida": "Blida", "Bouira": "Bouira", "Tamanrasset": "Tamanrasset", "Tebessa": "Tébessa",
    "Tlemcen": "Tlemcen", "Tiaret": "Tiaret", "Tizi Ouzou": "Tizi Ouzou", "Algiers": "Alger",
    "Djelfa": "Djelfa", "Jijel": "Jijel", "Setif": "Sétif", "Saida": "Saïda", "Skikda": "Skikda",
    "Sidi Bel Abbes": "Sidi Bel Abbès", "Annaba": "Annaba", "Guelma": "Guelma", "Constantine": "Constantine",
    "Medea": "Médéa", "Mostaganem": "Mostaganem", "Msila": "M'Sila", "Mascara": "Mascara",
    "Ouargla": "Ouargla", "Oran": "Oran", "El Bayadh": "El Bayadh", "Illizi": "Illizi",
    "Bordj Bou Arreridj": "Bordj Bou Arréridj", "Boumerdes": "Boumerdès", "El Tarf": "El Tarf",
    "Tindouf": "Tindouf", "Tissemsilt": "Tissemsilt", "El Oued": "El Oued", "Khenchela": "Khenchela",
    "Souk Ahras": "Souk Ahras", "Tipaza": "Tipaza", "Mila": "Mila", "Ain Defla": "Aïn Defla",
    "Naama": "Naâma", "Ain Temouchent": "Aïn Témouchent", "Ghardaia": "Ghardaïa", "Relizane": "Relizane",
    "Timimoun": "Timimoun", "Bordj Badji Mokhtar": "Bordj Badji Mokhtar", "Ouled Djellal": "Ouled Djellal",
    "Beni Abbes": "Béni Abbès", "In Salah": "In Salah", "In Guezzam": "In Guezzam",
    "Touggourt": "Touggourt", "Djanet": "Djanet", "El M'Ghair": "El M'Ghair", "El Meniaa": "El Meniaa",
}

count = 0
for commune in communes_data:
    if commune.get('level') != 3:
        continue
    
    # Get wilaya (level 1 ancestor)
    wilaya_en = ""
    daira_en = ""
    for ancestor in commune.get('ancestors', []):
        if ancestor.get('level') == 1:
            wilaya_en = ancestor['name']['en']
        elif ancestor.get('level') == 2:
            daira_en = ancestor['name']['en']
    
    wilaya_fr = en_to_fr.get(wilaya_en, "")
    if not wilaya_fr:
        print(f"Unknown wilaya: {wilaya_en}")
        continue
    
    wilaya_code = wilaya_code_map.get(wilaya_fr, "00")
    nom_fr = commune['name'].get('en', '')  # Use English name as French for now
    nom_ar = commune['name'].get('local', '')
    zip_codes = commune.get('zip_codes', [])
    zip_code = zip_codes[0] if zip_codes else ""
    
    # Get centroid from geometry if available (not in this data)
    lat = None
    lon = None
    
    c.execute('''INSERT OR REPLACE INTO communes (id, wilaya_code, nom_fr, nom_ar, daira, zip_code, latitude, longitude)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (commune['id'], wilaya_code, nom_fr, nom_ar, daira_en, zip_code, lat, lon))
    count += 1

conn.commit()
print(f"Inserted {count} communes")

# Verify
c.execute('SELECT COUNT(*) FROM communes')
print(f"Total communes: {c.fetchone()[0]}")

conn.close()