import sqlite3
import json

with open(r'C:\SANTE_DZ_SCRAPER\communes_algerie_officielles.json', 'r', encoding='utf-8') as f:
    communes_data = json.load(f)

# Collect all unique wilaya names from the data
wilayas_in_data = set()
for commune in communes_data:
    for ancestor in commune.get('ancestors', []):
        if ancestor.get('level') == 1:
            wilayas_in_data.add(ancestor['name']['en'])

# Mapping from corrupted JSON strings to official French names
corrupted_to_fr = {
    "Adrar": "Adrar", "Chlef": "Chlef", "Laghouat": "Laghouat", "Oum El Bouaghi": "Oum El Bouaghi",
    "Batna": "Batna", "B�ja�a": "Béjaïa", "Biskra": "Biskra", "B�char": "Béchar",
    "Blida": "Blida", "Bouira": "Bouira", "Tamanrasset": "Tamanrasset", "T�bessa": "Tébessa",
    "Tlemcen": "Tlemcen", "Tiaret": "Tiaret", "Tizi Ouzou": "Tizi Ouzou", "Alger": "Alger",
    "Djelfa": "Djelfa", "Jijel": "Jijel", "S�tif": "Sétif", "Sa�da": "Saïda", "Skikda": "Skikda",
    "Sidi Bel Abb�s": "Sidi Bel Abbès", "Annaba": "Annaba", "Guelma": "Guelma", "Constantine": "Constantine",
    "M�d�a": "Médéa", "Mostaganem": "Mostaganem", "M'Sila": "M'Sila", "Mascara": "Mascara",
    "Ouargla": "Ouargla", "Oran": "Oran", "El Bayadh": "El Bayadh", "Illizi": "Illizi",
    "Bordj Bou Arreridj": "Bordj Bou Arréridj", "Boumerd�s": "Boumerdès", "El Tarf": "El Tarf",
    "Tindouf": "Tindouf", "Tissemsilt": "Tissemsilt", "El Oued": "El Oued", "Khenchela": "Khenchela",
    "Souk Ahras": "Souk Ahras", "Tipaza": "Tipaza", "Mila": "Mila", "A�n Defla": "Aïn Defla",
    "Na�ma": "Naâma", "A�n T�mouchent": "Aïn Témouchent", "Gharda�a": "Ghardaïa", "Relizane": "Relizane",
    "Timimoun": "Timimoun", "Bordj Badji Mokhtar": "Bordj Badji Mokhtar", "Ouled Djellal": "Ouled Djellal",
    "B�ni Abb�s": "Béni Abbès", "In Salah": "In Salah", "In Guezzam": "In Guezzam",
    "Touggourt": "Touggourt", "Djanet": "Djanet", "El Meghaier": "El M'Ghair", "El Menia": "El Meniaa",
}

# Find missing
mapped = set(corrupted_to_fr.keys())
missing = wilayas_in_data - mapped
print(f"Missing wilayas: {sorted(missing)}")

# Check what the actual strings look like
for w in sorted(missing):
    print(f"  '{w}' -> bytes: {w.encode('utf-8')}")