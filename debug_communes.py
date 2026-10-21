import sqlite3
import json

with open(r'C:\SANTE_DZ_SCRAPER\communes_algerie_officielles.json', 'r', encoding='utf-8') as f:
    communes_data = json.load(f)

# The mapping works - all wilayas match
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

# Test the full chain
test_wilayas = ["Béjaïa", "Béchar", "Sétif", "Saïda", "Médéa", "Aïn Defla", "Naâma", "Aïn Témouchent", "Ghardaïa", "Sidi Bel Abbès", "Tébessa", "Boumerdès", "Béni Abbès", "El Meghaier", "El Menia"]
for w in test_wilayas:
    fr = corrupted_to_fr.get(w, "NOT FOUND")
    code = wilaya_code_map.get(fr, "NO CODE")
    print(f"  {w} -> {fr} -> {code}")

# Now check actual data
print("\nActual data processing:")
skipped_reasons = {}
for commune in communes_data:
    if commune.get('level') != 3:
        continue
    
    wilaya_en = ""
    for ancestor in commune.get('ancestors', []):
        if ancestor.get('level') == 1:
            wilaya_en = ancestor['name']['en']
            break
    
    fr = corrupted_to_fr.get(wilaya_en)
    if not fr:
        reason = f"no fr mapping for '{wilaya_en}'"
    else:
        code = wilaya_code_map.get(fr)
        if not code:
            reason = f"no code for '{fr}'"
        else:
            continue  # success
    skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1

print("\nSkip reasons:")
for reason, count in sorted(skipped_reasons.items(), key=lambda x: -x[1]):
    print(f"  {count}: {reason}")