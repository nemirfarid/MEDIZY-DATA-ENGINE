import sqlite3

# Check production DB
prod = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = prod.cursor()
c.execute('SELECT COUNT(*) FROM places;')
prod_count = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025';")
prod_miph = c.fetchone()[0]
prod.close()

# Check test DB
test = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db')
c = test.cursor()
c.execute('SELECT COUNT(*) FROM places;')
test_count = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025';")
test_miph = c.fetchone()[0]
test.close()

print(f'Production: total={prod_count}, MIPH_2025={prod_miph}')
print(f'Test: total={test_count}, MIPH_2025={test_miph}')
print(f'Identical: {prod_count == test_count and prod_miph == test_miph}')

# Also check backup
backup = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_audit_20261011_021419.db')
c = backup.cursor()
c.execute('SELECT COUNT(*) FROM places;')
backup_count = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025';")
backup_miph = c.fetchone()[0]
backup.close()
print(f'Backup: total={backup_count}, MIPH_2025={backup_miph}')
print(f'Backup matches production: {prod_count == backup_count and prod_miph == backup_miph}')