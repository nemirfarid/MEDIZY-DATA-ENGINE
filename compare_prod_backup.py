import sqlite3

# Compare production with backup row by row
conn_prod = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
conn_backup = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_audit_20261011_021419.db')

c_prod = conn_prod.cursor()
c_backup = conn_backup.cursor()

# Compare all rows
c_prod.execute('SELECT id, place_id, nom, wilaya, commune, latitude, longitude, source FROM places ORDER BY id')
prod_data = c_prod.fetchall()

c_backup.execute('SELECT id, place_id, nom, wilaya, commune, latitude, longitude, source FROM places ORDER BY id')
backup_data = c_backup.fetchall()

diff_count = 0
for p, b in zip(prod_data, backup_data):
    if p != b:
        diff_count += 1
        if diff_count <= 5:
            print('Diff {}: prod={} | backup={}'.format(diff_count, p, b))

print('Total row differences: {}'.format(diff_count))

# Also check place_id sets
c_prod.execute('SELECT place_id FROM places WHERE place_id IS NOT NULL ORDER BY place_id')
prod_ids = [r[0] for r in c_prod.fetchall()]

c_backup.execute('SELECT place_id FROM places WHERE place_id IS NOT NULL ORDER BY place_id')
backup_ids = [r[0] for r in c_backup.fetchall()]

print('Production place_ids: {}'.format(len(prod_ids)))
print('Backup place_ids:     {}'.format(len(backup_ids)))
print('Sets equal: {}'.format(set(prod_ids) == set(backup_ids)))

conn_prod.close()
conn_backup.close()