import sqlite3
import json

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# 1. Total counts
c.execute("SELECT count(*) FROM facilities")
total = c.fetchone()[0]

# 2. Wilayas and Communes
c.execute("SELECT count(DISTINCT wilaya), count(DISTINCT commune) FROM facilities")
wils, coms = c.fetchone()

# 3. GPS analysis
c.execute("SELECT count(*) FROM facilities WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND latitude != 0 AND longitude != 0")
with_valid_gps = c.fetchone()[0]

# Check bounding box of Algeria: Lat ~ 18° to 38°, Lon ~ -9° to 12°
c.execute("""
    SELECT count(*) FROM facilities 
    WHERE latitude BETWEEN 18.0 AND 38.5 
      AND longitude BETWEEN -9.0 AND 12.5
""")
in_algeria_bounds = c.fetchone()[0]

# 4. Phones
c.execute("SELECT count(*) FROM facilities WHERE telephone IS NOT NULL AND length(trim(telephone)) >= 8")
with_phone = c.fetchone()[0]

# 5. Categories breakdown
c.execute("SELECT categorie, count(*) FROM facilities GROUP BY categorie ORDER BY count(*) DESC")
categories = c.fetchall()

# 6. Sources breakdown
c.execute("SELECT source, count(*) FROM facilities GROUP BY source ORDER BY count(*) DESC")
sources = c.fetchall()

# 7. Communes table check
c.execute("SELECT count(*) FROM communes")
total_communes_in_table = c.fetchone()[0]

# Communes with 0 facilities
c.execute("""
    SELECT count(*) FROM communes 
    WHERE nom_fr NOT IN (SELECT DISTINCT commune FROM facilities WHERE commune IS NOT NULL)
""")
communes_without_fac = c.fetchone()[0]

# 8. Check place_id links to Google Maps
c.execute("SELECT count(*) FROM facilities WHERE place_id IS NOT NULL")
with_place_id = c.fetchone()[0]

conn.close()

audit_result = {
    "total_facilities": total,
    "wilayas_count": wils,
    "communes_represented": coms,
    "total_communes_ref": total_communes_in_table,
    "communes_without_facilities": communes_without_fac,
    "valid_gps_count": with_valid_gps,
    "valid_gps_percentage": round(with_valid_gps / total * 100, 2),
    "gps_within_algeria_bounds": in_algeria_bounds,
    "gps_within_bounds_percentage": round(in_algeria_bounds / total * 100, 2),
    "with_valid_phone": with_phone,
    "with_phone_percentage": round(with_phone / total * 100, 2),
    "with_place_id": with_place_id,
    "with_place_id_percentage": round(with_place_id / total * 100, 2),
    "categories": categories,
    "sources": sources
}

print(json.dumps(audit_result, indent=2, ensure_ascii=False))

