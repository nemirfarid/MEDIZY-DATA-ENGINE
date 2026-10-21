import sqlite3
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()
c.execute('SELECT DISTINCT categorie_recherche FROM places WHERE wilaya = "Biskra" ORDER BY categorie_recherche')
cats = c.fetchall()
print('Categories in Biskra:')
for cat in cats:
    print(' ', cat[0])
conn.close()