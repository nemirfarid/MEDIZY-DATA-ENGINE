import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Check bounds of Algeria (Latitude: 18.0 to 38.0, Longitude: -9.0 to 12.5)
c.execute("SELECT id, nom, latitude, longitude, wilaya FROM facilities WHERE latitude < 18.0 OR latitude > 38.0 OR longitude < -9.0 OR longitude > 12.5")
bad_geo = c.fetchall()
print(f"Coordinates outside Algeria boundaries: {len(bad_geo)}")
for b in bad_geo:
    print(b)

# Check coordinates in the Mediterranean sea:
# For Algeria coast: roughly if latitude > 36.95 and longitude between 0 and 9, or coastal bounds
# More specifically: latitude > 37.1 (except Cap Blanc / Jijel/Skikda tip which maxes at ~37.08)
c.execute("SELECT id, nom, latitude, longitude, wilaya FROM facilities WHERE latitude > 37.2")
sea_geo = c.fetchall()
print(f"Coordinates north of Algeria coastline (> 37.2): {len(sea_geo)}")
for s in sea_geo:
    print(s)

conn.close()

