import sqlite3
import pandas as pd
import json

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

print("1. Total facilities in DB:", c.execute("SELECT count(1) FROM facilities").fetchone()[0])

print("\n2. Breakdown by source:")
for r in c.execute("SELECT source, count(1) FROM facilities GROUP BY source").fetchall():
    print("  ", r)

print("\n3. Checking bounds (outside Algeria):")
out_of_bounds = c.execute("""
    SELECT count(1) FROM facilities 
    WHERE latitude < 18.0 OR latitude > 38.0 OR longitude < -9.0 OR longitude > 12.5
""").fetchone()[0]
print(f"  Out of bounds: {out_of_bounds}")

print("\n4. Checking sea drift (latitude > 37.1):")
sea = c.execute("SELECT count(1) FROM facilities WHERE latitude > 37.1").fetchone()[0]
print(f"  North of Algerian coast (> 37.1): {sea}")

print("\n5. Checking missing commune or wilaya:")
missing_geo = c.execute("""
    SELECT count(1) FROM facilities 
    WHERE wilaya IS NULL OR wilaya = '' OR commune IS NULL OR commune = '' OR commune = 'nan'
""").fetchone()[0]
print(f"  Missing Wilaya or Commune: {missing_geo}")

print("\n6. Checking Dr Ben Tata and Sidi Ali:")
c.execute("SELECT id, nom, categorie, latitude, longitude, commune, wilaya FROM facilities WHERE nom LIKE '%bentata%' OR nom LIKE '%ben%tata%'")
for r in c.fetchall():
    print("  ", r)

c.execute("SELECT count(1) FROM facilities WHERE commune = 'Sidi Ali'")
print(f"  Total facilities in Sidi Ali: {c.fetchone()[0]}")

conn.close()

