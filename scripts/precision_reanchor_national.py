import sqlite3
import math

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def run():
    conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
    c = conn.cursor()

    # Load all communes
    c.execute('''
        SELECT nom_fr, wilaya_code, latitude, longitude 
        FROM communes 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ''')
    communes = c.fetchall()
    print(f"Loaded {len(communes)} reference communes.")

    # Mapping wilaya_code -> wilaya name
    c.execute('''
        SELECT DISTINCT wilaya_code, wilaya 
        FROM facilities 
        WHERE wilaya IS NOT NULL AND wilaya_code IS NOT NULL
        GROUP BY wilaya_code
    ''')
    w_map = dict(c.fetchall())

    # Find facilities where facility's GPS is > 15 km away from its declared commune
    c.execute('''
        SELECT f.id, f.nom, f.latitude, f.longitude, f.commune, f.wilaya_code, cm.latitude, cm.longitude
        FROM facilities f
        JOIN communes cm ON f.commune = cm.nom_fr AND f.wilaya_code = cm.wilaya_code
        WHERE f.latitude IS NOT NULL AND f.longitude IS NOT NULL
          AND cm.latitude IS NOT NULL AND cm.longitude IS NOT NULL
    ''')
    rows = c.fetchall()
    print(f"Checking {len(rows)} facilities...")

    misplaced = []
    for fid, nom, flat, flon, fcom, fwc, cmlat, cmlon in rows:
        d = haversine_km(flat, flon, cmlat, cmlon)
        if d > 12.0:  # Distance greater than 12 km from assigned commune centroid
            misplaced.append((fid, flat, flon, fcom, fwc, d))

    print(f"Found {len(misplaced)} facilities located > 12km from their assigned commune.")

    updates = []
    for fid, flat, flon, old_com, old_wc, old_dist in misplaced:
        # Find nearest commune
        best_commune = None
        min_dist = float('inf')
        for c_nom, c_wc, clat, clon in communes:
            dist = haversine_km(flat, flon, clat, clon)
            if dist < min_dist:
                min_dist = dist
                best_commune = (c_nom, c_wc)

        if best_commune and min_dist < 25.0:
            new_com, new_wc = best_commune
            new_wname = w_map.get(new_wc, 'Algérie')
            if new_com != old_com or new_wc != old_wc:
                updates.append((new_com, new_wc, new_wname, fid))

    print(f"Applying {len(updates)} precision re-anchoring updates...")
    c.executemany('''
        UPDATE facilities 
        SET commune = ?, wilaya_code = ?, wilaya = ?
        WHERE id = ?
    ''', updates)
    conn.commit()

    # Rebuild indexes
    print("Rebuilding R-Tree and FTS index...")
    c.execute("DELETE FROM facilities_rtree")
    c.execute('''
        INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
        SELECT id, latitude, latitude, longitude, longitude 
        FROM facilities 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ''')
    try:
        c.execute("INSERT INTO facilities_fts(facilities_fts) VALUES('rebuild')")
    except Exception as e:
        print("FTS notice:", e)

    conn.commit()
    conn.close()
    print("Precision reanchoring complete!")

if __name__ == '__main__':
    run()

