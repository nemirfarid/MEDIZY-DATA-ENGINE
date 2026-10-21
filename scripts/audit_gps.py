import sqlite3

db = sqlite3.connect(r'assets\data\sante_dz_bundled.db')
cur = db.cursor()

# Overall stats
cur.execute('SELECT COUNT(id), MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM facilities')
count_all, min_lat, max_lat, min_lon, max_lon = cur.fetchone()
print(f'GLOBAL ({count_all}): Lat: [{min_lat:.4f}, {max_lat:.4f}], Lon: [{min_lon:.4f}, {max_lon:.4f}]')

# Mostaganem stats
cur.execute("SELECT COUNT(id), MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM facilities WHERE wilaya_code = '27'")
count_m, min_lat_m, max_lat_m, min_lon_m, max_lon_m = cur.fetchone()
print(f'MOSTAGANEM (27): {count_m} etablissements | Lat: [{min_lat_m:.4f}, {max_lat_m:.4f}], Lon: [{min_lon_m:.4f}, {max_lon_m:.4f}]')

# Check first 5 records in Mostaganem
cur.execute("SELECT nom, categorie, commune, latitude, longitude FROM facilities WHERE wilaya_code = '27' LIMIT 5")
for r in cur.fetchall():
    print('  Sample:', r)
