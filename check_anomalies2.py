import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cursor = conn.cursor()

# Search for the 4th anomaly: Cabinet Médico chirurgical in Naâma
cursor.execute('''SELECT id, nom, wilaya, latitude, longitude, google_maps_url, place_id 
                  FROM places WHERE wilaya = "Naama" AND (nom LIKE "%Medico%" OR nom LIKE "%médico%" OR nom LIKE "%chirurgical%" OR nom LIKE "%Chirurgical%")''')
rows = cursor.fetchall()
for row in rows:
    print(f"  ID: {row[0]}")
    print(f"  Nom: {row[1]}")
    print(f"  Wilaya: {row[2]}")
    print(f"  GPS: {row[3]}, {row[4]}")
    print(f"  URL: {row[5]}")
    print(f"  Place ID: {row[6]}")
    print()

# Also search more broadly in Naama for any "cabinet" or "clinique" with suspicious GPS
cursor.execute('''SELECT id, nom, wilaya, latitude, longitude FROM places 
WHERE wilaya = "Naama" AND (latitude < 18.9 OR latitude > 37.5 OR longitude < -8.7 OR longitude > 12.0)''')
rows = cursor.fetchall()
print(f"Naama entries outside Algeria bounds: {len(rows)}")
for row in rows:
    print(f"  ID: {row[0]}, Nom: {row[1]}, GPS: {row[3]}, {row[4]}")

# Check all entries in the DB with the old problematic coordinates from URLs
# The URLs contain the old coords: 30.3866662,-9.5085172 (Morocco), 45.4034505,4.3646541 (France), 
# 41.2073783,0.1778046 (Spain), 30.6959409,-26.4286261 (South Africa)
print("\n=== Checking if any current lat/lon match OLD anomalous coords ===")
old_coords = [
    (30.3866662, -9.5085172),   # Morocco
    (45.4034505, 4.3646541),    # France  
    (41.2073783, 0.1778046),    # Spain
    (30.6959409, -26.4286261),  # South Africa
]
for lat, lon in old_coords:
    cursor.execute('''SELECT id, nom, wilaya, latitude, longitude FROM places 
                      WHERE ABS(latitude - ?) < 0.001 AND ABS(longitude - ?) < 0.001''', (lat, lon))
    rows = cursor.fetchall()
    if rows:
        print(f"  Found entry with old coords ({lat}, {lon}):")
        for row in rows:
            print(f"    ID: {row[0]}, Nom: {row[1]}, Wilaya: {row[2]}, GPS: {row[3]}, {row[4]}")
    else:
        print(f"  No entry currently has old coords ({lat}, {lon}) - GOOD")

conn.close()