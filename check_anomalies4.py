import sqlite3
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cursor = conn.cursor()

# Search for the 4th anomaly in Naama specifically
cursor.execute('''SELECT id, nom, wilaya, latitude, longitude, google_maps_url 
                  FROM places WHERE wilaya = "Na�ma" AND (nom LIKE "%Medico%" OR nom LIKE "%médico%" OR nom LIKE "%chirurgical%" OR nom LIKE "%Chirurgical%")''')
rows = cursor.fetchall()
print(f"Entries with 'medico' or 'chirurgical' in Naama: {len(rows)}")
for row in rows:
    print(f"  ID: {row[0]}")
    print(f"  Nom: {row[1]}")
    print(f"  Wilaya: {row[2]}")
    print(f"  GPS: {row[3]}, {row[4]}")
    print(f"  URL: {row[5]}")
    print()

# Also check all Naama entries for any with suspicious GPS
cursor.execute('''SELECT id, nom, wilaya, latitude, longitude FROM places 
WHERE wilaya = "Na�ma" AND (latitude < 18.9 OR latitude > 37.5 OR longitude < -8.7 OR longitude > 12.0)''')
rows = cursor.fetchall()
print(f"Naama entries outside Algeria bounds: {len(rows)}")
for row in rows:
    print(f"  ID: {row[0]}, Nom: {row[1]}, GPS: {row[3]}, {row[4]}")

# Check the OLD coordinate from report: 41.2073783, 0.1778046 (Spain)
cursor.execute('''SELECT id, nom, wilaya, latitude, longitude FROM places 
WHERE ABS(latitude - 41.207) < 0.01 AND ABS(longitude - 0.178) < 0.01''')
rows = cursor.fetchall()
print(f"\nEntries near old Spain coords (41.207, 0.178): {len(rows)}")
for row in rows:
    print(f"  ID: {row[0]}, Nom: {row[1]}, Wilaya: {row[2]}, GPS: {row[3]}, {row[4]}")

conn.close()