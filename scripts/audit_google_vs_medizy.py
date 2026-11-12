import sqlite3
import pandas as pd
import numpy as np

# Load Scraper Google Maps
conn_sc = sqlite3.connect('medizy_scraper.db')
c_sc = conn_sc.cursor()
c_sc.execute("SELECT id, place_id, nom, latitude, longitude, telephone, wilaya, commune FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
scraper_places = c_sc.fetchall()
conn_sc.close()

# Load Medizy facilities
conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_app = conn_app.cursor()
c_app.execute("SELECT id, nom, latitude, longitude, place_id, telephone, wilaya, commune FROM facilities")
app_facilities = c_app.fetchall()
conn_app.close()

print(f"Scraper Google Places: {len(scraper_places)}")
print(f"App Facilities: {len(app_facilities)}")

# Check matching methods
app_by_pid = {}
app_by_phone = {}
app_by_name = {}

for f in app_facilities:
    fid, fnom, flat, flon, fpid, fphone, fwil, fcom = f
    if fpid:
        app_by_pid[str(fpid)] = f
    if fphone and len(str(fphone).strip()) > 7:
        clean_phone = ''.join(c for c in str(fphone) if c.isdigit())
        if len(clean_phone) >= 8:
            app_by_phone[clean_phone[-8:]] = f
    if fnom:
        clean_name = fnom.strip().lower()
        app_by_name[(fwil.lower() if fwil else '', clean_name)] = f

matched_places = 0
unmatched_places = []
dist_deviations = []

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp/2.0)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2.0)**2
    return 2.0 * R * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))

for p in scraper_places:
    pid, pchij, pnom, plat, plon, pphone, pwil, pcom = p
    match = None
    
    # 1. By place_id (numeric or ChIJ)
    if str(pid) in app_by_pid:
        match = app_by_pid[str(pid)]
    elif pchij and pchij in app_by_pid:
        match = app_by_pid[pchij]
    
    # 2. By phone
    if not match and pphone:
        clean_p = ''.join(c for c in str(pphone) if c.isdigit())
        if len(clean_p) >= 8 and clean_p[-8:] in app_by_phone:
            match = app_by_phone[clean_p[-8:]]
            
    # 3. By exact name + wilaya
    if not match and pnom:
        key = (pwil.lower() if pwil else '', pnom.strip().lower())
        if key in app_by_name:
            match = app_by_name[key]
            
    if match:
        matched_places += 1
        fid, fnom, flat, flon, fpid, fphone, fwil, fcom = match
        dist = haversine(flat, flon, plat, plon)
        if dist >= 1.0:
            dist_deviations.append((p, match, dist))
    else:
        unmatched_places.append(p)

print(f"Matched Google places to Medizy: {matched_places}")
print(f"Google places with distance >= 1m from Medizy: {len(dist_deviations)}")
print(f"Google places NOT in Medizy at all: {len(unmatched_places)}")

if dist_deviations:
    print("\nSample distance deviations (Google vs Medizy):")
    for p, m, d in dist_deviations[:5]:
        print(f"Google: {p[2]} ({p[3]}, {p[4]}) vs Medizy: {m[1]} ({m[2]}, {m[3]}) -> Dist: {d:.2f}m")

if unmatched_places:
    print("\nSample Google places missing from Medizy:")
    for p in unmatched_places[:5]:
        print(f"ID {p[0]}: {p[2]} ({p[6]}, {p[7]}) [{p[3]}, {p[4]}]")

