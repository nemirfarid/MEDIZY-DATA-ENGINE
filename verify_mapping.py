import sqlite3
import json

with open(r'C:\SANTE_DZ_SCRAPER\communes_algerie_officielles.json', 'r', encoding='utf-8') as f:
    communes_data = json.load(f)

# The JSON has proper UTF-8. The display issue is terminal encoding.
# Let's use the actual Unicode strings in the mapping.
corrupted_to_fr = {
    "Adrar": "Adrar", "Chlef": "Chlef", "Laghouat": "Laghouat", "Oum El Bouaghi": "Oum El Bouaghi",
    "Batna": "Batna", "Béjaïa": "Béjaïa", "Biskra": "Biskra", "Béchar": "Béchar",
    "Blida": "Blida", "Bouira": "Bouira", "Tamanrasset": "Tamanrasset", "Tébessa": "Tébessa",
    "Tlemcen": "Tlemcen", "Tiaret": "Tiaret", "Tizi Ouzou": "Tizi Ouzou", "Alger": "Alger",
    "Djelfa": "Djelfa", "Jijel": "Jijel", "Sétif": "Sétif", "Saïda": "Saïda", "Skikda": "Skikda",
    "Sidi Bel Abbès": "Sidi Bel Abbès", "Annaba": "Annaba", "Guelma": "Guelma", "Constantine": "Constantine",
    "Médéa": "Médéa", "Mostaganem": "Mostaganem", "M'Sila": "M'Sila", "Mascara": "Mascara",
    "Ouargla": "Ouargla", "Oran": "Oran", "El Bayadh": "El Bayadh", "Illizi": "Illizi",
    "Bordj Bou Arreridj": "Bordj Bou Arréridj", "Boumerdès": "Boumerdès", "El Tarf": "El Tarf",
    "Tindouf": "Tindouf", "Tissemsilt": "Tissemsilt", "El Oued": "El Oued", "Khenchela": "Khenchela",
    "Souk Ahras": "Souk Ahras", "Tipaza": "Tipaza", "Mila": "Mila", "Aïn Defla": "Aïn Defla",
    "Naâma": "Naâma", "Aïn Témouchent": "Aïn Témouchent", "Ghardaïa": "Ghardaïa", "Relizane": "Relizane",
    "Timimoun": "Timimoun", "Bordj Badji Mokhtar": "Bordj Badji Mokhtar", "Ouled Djellal": "Ouled Djellal",
    "Béni Abbès": "Béni Abbès", "In Salah": "In Salah", "In Guezzam": "In Guezzam",
    "Touggourt": "Touggourt", "Djanet": "Djanet", "El Meghaier": "El M'Ghair", "El Menia": "El Meniaa",
}

# Verify keys match
wilayas_in_data = set()
for commune in communes_data:
    for ancestor in commune.get('ancestors', []):
        if ancestor.get('level') == 1:
            wilayas_in_data.add(ancestor['name']['en'])

print("Wilayas in data that match mapping:")
for w in sorted(wilayas_in_data):
    if w in corrupted_to_fr:
        print(f"  OK: '{w}' -> {corrupted_to_fr[w]}")
    else:
        print(f"  MISSING: '{w}'")

print(f"\nMapping keys not in data:")
for w in sorted(corrupted_to_fr.keys()):
    if w not in wilayas_in_data:
        print(f"  EXTRA: '{w}'")

# Test lookup
print("\nTest lookups:")
for w in ["Béjaïa", "Béchar", "Sétif", "Saïda", "Médéa", "Aïn Defla", "Naâma", "Aïn Témouchent", "Ghardaïa", "Sidi Bel Abbès", "Tébessa", "Boumerdès", "Béni Abbès", "El Meghaier", "El Menia"]:
    if w in corrupted_to_fr:
        print(f"  '{w}' -> {corrupted_to_fr[w]}")
    else:
        print(f"  '{w}' NOT FOUND in mapping")