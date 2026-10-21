import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cursor = conn.cursor()

# Check wilaya names in DB
cursor.execute('SELECT DISTINCT wilaya FROM places ORDER BY wilaya')
wilayas = [row[0] for row in cursor.fetchall()]
print("Wilayas in DB:")
for w in wilayas:
    print(f"  '{w}'")

# Search for Cabinet Médico chirurgical in any wilaya
cursor.execute('''SELECT id, nom, wilaya, latitude, longitude, google_maps_url 
                  FROM places WHERE nom LIKE "%Medico%" OR nom LIKE "%médico%" OR nom LIKE "%chirurgical%" OR nom LIKE "%Chirurgical%"''')
rows = cursor.fetchall()
print(f"\nEntries with 'medico' or 'chirurgical' in name: {len(rows)}")
for row in rows:
    print(f"  ID: {row[0]}, Nom: {row[1]}, Wilaya: {row[2]}, GPS: {row[3]}, {row[4]}")

# Also search for "Cabinet" + "chirurgical" or "medico" in Naama/Naâma
cursor.execute('''SELECT id, nom, wilaya, latitude, longitude FROM places 
WHERE wilaya LIKE "%Naam%" AND nom LIKE "%Cabinet%"''')
rows = cursor.fetchall()
print(f"\nCabinets in Naama: {len(rows)}")
for row in rows:
    print(f"  ID: {row[0]}, Nom: {row[1]}, Wilaya: {row[2]}, GPS: {row[3]}, {row[4]}")

conn.close()