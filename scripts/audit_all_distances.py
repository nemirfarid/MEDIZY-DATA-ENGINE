import sqlite3
import numpy as np

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp/2.0)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2.0)**2
    return 2.0 * R * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))

conn_sc = sqlite3.connect('medizy_scraper.db')
c_sc = conn_sc.cursor()
c_sc.execute("SELECT id, place_id, nom, latitude, longitude FROM places WHERE latitude IS NOT NULL")
places_by_id = {}
places_by_chij = {}
for pid, chij, nom, lat, lon in c_sc.fetchall():
    places_by_id[str(pid)] = (nom, lat, lon)
    if chij:
        places_by_chij[chij] = (nom, lat, lon)
conn_sc.close()

conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_app = conn_app.cursor()
c_app.execute("SELECT id, nom, latitude, longitude, place_id, commune, wilaya FROM facilities")
facs = c_app.fetchall()
conn_app.close()

dist_gt_1m = []
unmatched = []

for fid, fnom, flat, flon, fpid, fcom, fwil in facs:
    matched = None
    if fpid in places_by_id:
        matched = places_by_id[fpid]
    elif fpid in places_by_chij:
        matched = places_by_chij[fpid]
    
    if matched:
        gnom, glat, glon = matched
        d = haversine(flat, flon, glat, glon)
        if d >= 1.0:
            dist_gt_1m.append((fid, fnom, fcom, fwil, flat, flon, glat, glon, d))
    else:
        unmatched.append((fid, fnom, fcom, fwil, flat, flon))

print(f"Total facilities: {len(facs)}")
print(f"Matched with scraper places: {len(facs) - len(unmatched)}")
print(f"Distance >= 1 meter: {len(dist_gt_1m)}")
print(f"Unmatched facilities: {len(unmatched)}")

if dist_gt_1m:
    print("\nSample distance >= 1m:")
    for item in dist_gt_1m[:10]:
        print(f"ID {item[0]}: {item[1]} ({item[2]}, {item[3]}) -> Dist: {item[8]:.1f}m (App: {item[4]}, {item[5]} vs Google: {item[6]}, {item[7]})")

