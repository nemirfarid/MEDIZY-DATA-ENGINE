import sqlite3
import pandas as pd
import json

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# 1. Total facilities and sources
print("=== AUDIT BASE DE DONNÉES MEDIZY ===")
total = c.execute("SELECT count(1) FROM facilities").fetchone()[0]
print(f"Total des structures : {total}")

sources = c.execute("SELECT source, count(1) FROM facilities GROUP BY source").fetchall()
for s in sources:
    print(f"  - Source '{s[0]}' : {s[1]} structures")

# 2. Check for any synthetic or test data
test_count = c.execute("SELECT count(1) FROM facilities WHERE source LIKE '%test%' OR source LIKE '%annuaire sanitaire national%'").fetchone()[0]
print(f"\nStructures de test ou synthétiques résiduelles : {test_count}")

# 3. Geo boundaries check
out_of_algeria = c.execute("""
    SELECT count(1) FROM facilities 
    WHERE latitude < 18.0 OR latitude > 38.0 OR longitude < -9.0 OR longitude > 12.5
""").fetchone()[0]
print(f"Structures hors d'Algérie : {out_of_algeria}")

mediterranean = c.execute("SELECT count(1) FROM facilities WHERE latitude > 37.1").fetchone()[0]
print(f"Structures dérivant en mer Méditerranée (> 37.1° N) : {mediterranean}")

# 4. Check Google Maps exact GPS sync
gmaps_count = c.execute("SELECT count(1) FROM facilities WHERE source = 'Google Maps Extractor'").fetchone()[0]
print(f"\nStructures Google Maps certifiées : {gmaps_count}")

# 5. Check Wilayas and Communes
missing_w = c.execute("SELECT count(1) FROM facilities WHERE wilaya IS NULL OR trim(wilaya) = ''").fetchone()[0]
missing_c = c.execute("SELECT count(1) FROM facilities WHERE commune IS NULL OR trim(commune) = ''").fetchone()[0]
print(f"Structures sans Wilaya : {missing_w}")
print(f"Structures sans Commune : {missing_c}")

# 6. Check Dr Ben Tata & Sidi Ali urban area
print("\nZoom sur Dr Ben Tata et Sidi Ali :")
c.execute("SELECT id, nom, categorie, latitude, longitude, commune, source FROM facilities WHERE nom LIKE '%ben%tata%'")
for r in c.fetchall():
    print("  ", r)

c.execute("SELECT id, nom, categorie, latitude, longitude FROM facilities WHERE commune = 'Sidi Ali'")
sidi_facilities = c.fetchall()
print(f"\nTotal des structures réelles à Sidi Ali ville : {len(sidi_facilities)}")
for sf in sidi_facilities:
    print(f"  - {sf[1]} ({sf[2]}) -> Lat: {sf[3]}, Lon: {sf[4]}")

conn.close()

