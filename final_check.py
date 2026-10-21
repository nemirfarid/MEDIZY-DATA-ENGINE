import sqlite3
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db')
c = conn.cursor()

# Check categories in Biskra now
c.execute('SELECT DISTINCT categorie_recherche, COUNT(*) FROM places WHERE wilaya = "Biskra" GROUP BY categorie_recherche ORDER BY COUNT(*) DESC')
cats = c.fetchall()
print('Biskra categories after import:')
for cat, count in cats:
    print('  {}: {}'.format(cat, count))

# Check communes coverage
c.execute('SELECT DISTINCT commune, COUNT(*) FROM places WHERE wilaya = "Biskra" AND commune IS NOT NULL AND commune != "" GROUP BY commune ORDER BY COUNT(*) DESC')
communes = c.fetchall()
print('\nBiskra communes covered:')
for comm, count in communes:
    print('  {}: {}'.format(comm, count))
print('  Total communes: {}'.format(len(communes)))

conn.close()