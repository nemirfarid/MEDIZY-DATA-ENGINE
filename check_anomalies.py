import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cursor = conn.cursor()

# Check the 4 specific anomalies from the report
anomalies = [
    ('Clinique Adrar Dar Salam Agadir', 'Adrar'),
    ('Orthophoniste Mila', 'Mila'),
    ('Cabinet M', 'Naama'),  # Cabinet Médico chirurgical
    ('ORL Dr Yassine BALHI', 'Tizi Ouzou'),
]

print("=== Checking 4 reported anomalies ===")
for name_part, wilaya in anomalies:
    cursor.execute('''SELECT id, nom, wilaya, latitude, longitude, google_maps_url, place_id 
                      FROM places WHERE wilaya = ? AND nom LIKE ?''', (wilaya, f'%{name_part}%'))
    rows = cursor.fetchall()
    for row in rows:
        print(f"  ID: {row[0]}")
        print(f"  Nom: {row[1]}")
        print(f"  Wilaya: {row[2]}")
        print(f"  GPS: {row[3]}, {row[4]}")
        print(f"  URL: {row[5]}")
        print(f"  Place ID: {row[6]}")
        print()

# Also check all GPS outside reasonable Algeria bounds (more precise)
# Algeria roughly: lat 18.9 to 37.5, lon -8.7 to 12.0
cursor.execute('''SELECT id, nom, wilaya, latitude, longitude FROM places 
WHERE (latitude < 18.9 OR latitude > 37.5 OR longitude < -8.7 OR longitude > 12.0)''')
gps_out = cursor.fetchall()
print(f'GPS outside precise Algeria bounds: {len(gps_out)}')
for row in gps_out:
    print(f"  ID: {row[0]}, Nom: {row[1]}, Wilaya: {row[2]}, GPS: {row[3]}, {row[4]}")

# Check the 4 specific from the previous verification output
print("\n=== Checking specific 4 from post_phase5_verify note ===")
# The note says "4 entries need manual verification" but GPS outside Algeria = 0
# Let's check if there are entries with GPS that are suspiciously far from their wilaya
# Get wilaya centroids and check distances
cursor.execute('''SELECT id, nom, wilaya, latitude, longitude FROM places 
WHERE wilaya IN ('Adrar', 'Mila', 'Naama', 'Tizi Ouzou') 
AND (nom LIKE '%Adrar Dar Salam%' OR nom LIKE '%Orthophoniste%' OR nom LIKE '%Medico chirurgical%' OR nom LIKE '%ORL Dr Yassine BALHI%')''')
rows = cursor.fetchall()
for row in rows:
    print(f"  ID: {row[0]}, Nom: {row[1]}, Wilaya: {row[2]}, GPS: {row[3]}, {row[4]}")

conn.close()