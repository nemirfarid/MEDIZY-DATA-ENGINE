import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM places')
print('Total entries:', cursor.fetchone()[0])

cursor.execute('SELECT COUNT(DISTINCT wilaya) FROM places')
print('Wilayas:', cursor.fetchone()[0])

cursor.execute('SELECT COUNT(DISTINCT categorie_recherche) FROM places')
print('Categories:', cursor.fetchone()[0])

cursor.execute('SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL')
print('With GPS:', cursor.fetchone()[0])

cursor.execute('SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ""')
print('With phone:', cursor.fetchone()[0])

cursor.execute('SELECT COUNT(*) FROM places WHERE adresse IS NOT NULL AND adresse != ""')
print('With address:', cursor.fetchone()[0])

cursor.execute('SELECT COUNT(*) FROM places WHERE site_web IS NOT NULL AND site_web != ""')
print('With website:', cursor.fetchone()[0])

cursor.execute('SELECT google_maps_url, COUNT(*) as c FROM places GROUP BY google_maps_url HAVING c > 1')
dups_url = cursor.fetchall()
print('Duplicate URLs:', len(dups_url))

cursor.execute('SELECT place_id, COUNT(*) as c FROM places WHERE place_id IS NOT NULL AND place_id != "" GROUP BY place_id HAVING c > 1')
dups_place = cursor.fetchall()
print('Duplicate place_ids:', len(dups_place))

cursor.execute('''SELECT id, nom, wilaya, latitude, longitude FROM places 
WHERE (latitude < 18 OR latitude > 37 OR longitude < -9 OR longitude > 12)''')
gps_out = cursor.fetchall()
print('GPS outside Algeria bounds:', len(gps_out))
for row in gps_out:
    print('  ', row)

# Check name_status distribution
cursor.execute('SELECT name_status, COUNT(*) FROM places GROUP BY name_status')
print('name_status distribution:', cursor.fetchall())

conn.close()