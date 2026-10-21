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

print("Wilayas in data:")
for w in sorted(wilayas_in_data):
    print(f"  '{w}'")

# Check which ones are missing from my mapping
mapped = {
    "Adrar", "Chlef", "Laghouat", "Oum El Bouaghi", "Batna", "Bejaia", "Biskra", "Bechar",
    "Blida", "Bouira", "Tamanrasset", "Tebessa", "Tlemcen", "Tiaret", "Tizi Ouzou", "Alger",
    "Djelfa", "Jijel", "Setif", "Saida", "Skikda", "Sidi Bel Abbes", "Annaba", "Guelma", 
    "Constantine", "Medea", "Mostaganem", "Msila", "Mascara", "Ouargla", "Oran", "El Bayadh",
    "Illizi", "Bordj Bou Arreridj", "Boumerdes", "El Tarf", "Tindouf", "Tissemsilt", "El Oued",
    "Khenchela", "Souk Ahras", "Tipaza", "Mila", "Ain Defla", "Naama", "Ain Temouchent",
    "Ghardaia", "Relizane", "Timimoun", "Bordj Badji Mokhtar", "Ouled Djellal", "Beni Abbes",
    "In Salah", "In Guezzam", "Touggourt", "Djanet", "El Meghaier", "El Menia"
}

missing = wilayas_in_data - mapped
print(f"\nMissing from mapping: {sorted(missing)}")
extra = mapped - wilayas_in_data
print(f"Extra in mapping: {sorted(extra)}")