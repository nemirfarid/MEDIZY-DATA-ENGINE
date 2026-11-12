import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Check sources in DB
c.execute("SELECT source, count(1) FROM facilities GROUP BY source")
print("Current sources in DB:", c.fetchall())

# Let's inspect the 28073 Google Maps Extractor records:
# How many have wilaya, commune, latitude, longitude?
c.execute("""
    SELECT count(1) FROM facilities 
    WHERE source = 'Google Maps Extractor' AND latitude IS NOT NULL AND longitude IS NOT NULL
""")
print("Google Maps Extractor with valid coords:", c.fetchone()[0])

# Are there any fake or synthetic sources left?
# 1. 'Google Maps Sidi Ali Test' (20 artificial offset coordinates) -> MUST BE REMOVED!
# 2. 'OpenStreetMap Verified' (77 elements inserted with hardcoded commune='Sidi Ali') -> check their coordinates!
c.execute("SELECT id, nom, latitude, longitude, commune FROM facilities WHERE source = 'Google Maps Sidi Ali Test'")
test_rows = c.fetchall()
print(f"Artificial 'Google Maps Sidi Ali Test' records: {len(test_rows)}")

conn.close()

