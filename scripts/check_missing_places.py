import sqlite3

conn_sc = sqlite3.connect('medizy_scraper.db')
c_sc = conn_sc.cursor()
c_sc.execute("SELECT id, place_id, nom, latitude, longitude FROM places WHERE latitude IS NOT NULL")
places_all = c_sc.fetchall()
conn_sc.close()

conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_app = conn_app.cursor()
c_app.execute("SELECT place_id FROM facilities WHERE place_id IS NOT NULL")
existing_pids = {r[0] for r in c_app.fetchall()}
conn_app.close()

missing_places = []
for pid, chij, nom, lat, lon in places_all:
    if str(pid) not in existing_pids and (not chij or chij not in existing_pids):
        missing_places.append((pid, chij, nom, lat, lon))

print(f"Total Google places in scraper: {len(places_all)}")
print(f"Places already linked in Medizy facilities: {len(places_all) - len(missing_places)}")
print(f"Places NOT in Medizy facilities: {len(missing_places)}")

if missing_places:
    print("\nSample missing places:")
    for mp in missing_places[:10]:
        print(mp)

