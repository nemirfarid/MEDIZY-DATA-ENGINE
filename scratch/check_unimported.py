import sqlite3, json

con = sqlite3.connect('file:C:/SANTE_DZ_SCRAPER/medizy_scraper.db?mode=ro', uri=True)
cur = con.cursor()
cur.execute('SELECT place_id FROM places WHERE place_id IS NOT NULL')
prod_pids = set(r[0] for r in cur.fetchall())
cur.execute('SELECT COUNT(*) FROM places')
print('Current count:', cur.fetchone()[0])
con.close()

with open(r'D:\SANTE_DZ_EXPORTS\1sante_raw_listings.json', 'r', encoding='utf-8') as f:
    listings = json.load(f)

unimported_1sante = [item for item in listings if f"1sante:at_biz_dir:{item.get('id')}" not in prod_pids]
print('Unimported 1sante listings:', len(unimported_1sante))
