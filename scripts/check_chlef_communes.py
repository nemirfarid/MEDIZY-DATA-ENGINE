import sqlite3

conn = sqlite3.connect('medizy_scraper.db')
c = conn.cursor()
c.execute("SELECT id, name_fr, name_ar, latitude, longitude FROM communes WHERE wilaya_id = 2")
communes = c.fetchall()
print(f"Total official communes in Chlef (wilaya_id=2): {len(communes)}")
for com in communes:
    print(com)

