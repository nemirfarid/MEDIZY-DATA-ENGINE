import sqlite3

conn_sc = sqlite3.connect('medizy_scraper.db')
c_sc = conn_sc.cursor()
c_sc.execute("SELECT count(*) FROM places")
total_places = c_sc.fetchone()[0]
print(f"Total places in medizy_scraper.db: {total_places}")

c_sc.execute("SELECT count(*) FROM places WHERE place_id LIKE 'ChIJ%'")
chij_places = c_sc.fetchone()[0]
print(f"Google Maps places (ChIJ): {chij_places}")

conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_app = conn_app.cursor()
c_app.execute("SELECT count(*) FROM facilities")
total_fac = c_app.fetchone()[0]
print(f"Total facilities in sante_dz_bundled.db: {total_fac}")

# How many facilities have place_id in places table?
# places has two kinds: place_id like 'ChIJ%' and id as int
c_app.execute("SELECT place_id FROM facilities WHERE place_id IS NOT NULL")
fac_pids = [r[0] for r in c_app.fetchall()]

c_sc.execute("SELECT id, place_id FROM places")
places_all = c_sc.fetchall()
p_ids = {str(r[0]) for r in places_all}
p_chij = {r[1] for r in places_all if r[1]}

matched_by_id = sum(1 for pid in fac_pids if pid in p_ids)
matched_by_chij = sum(1 for pid in fac_pids if pid in p_chij)

print(f"Matched by numeric ID: {matched_by_id}")
print(f"Matched by ChIJ place_id: {matched_by_chij}")

conn_sc.close()
conn_app.close()

