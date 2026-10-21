import sqlite3
import pandas as pd

# Load geocoding data
df = pd.read_csv(r"D:\SANTE_DZ_EXPORTS\geocoding_applied.csv", dtype=str).fillna("")
print(f"Loaded {len(df)} geocoded entries")

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Update places with commune data from geocoding
updated = 0
for _, row in df.iterrows():
    place_id = row['id']
    commune = row['commune']
    confidence = row['confidence']
    distance = row['distance_km']
    
    if commune and commune.strip():
        c.execute('''UPDATE places SET commune = ?, commune_source = ?, commune_confidence = ?, commune_updated_at = datetime("now")
                     WHERE id = ?''',
                  (commune, f"geocoding_centroid_{confidence.lower()}", 
                   1.0 if confidence == "HIGH" else 0.7 if confidence == "MEDIUM" else 0.4,
                   place_id))
        if c.rowcount > 0:
            updated += 1

conn.commit()
print(f"Updated {updated} entries with commune data")

# Verify
c.execute('SELECT COUNT(*) FROM places WHERE commune IS NOT NULL AND commune != ""')
print(f"Total with commune: {c.fetchone()[0]}")

c.execute('SELECT COUNT(*) FROM places')
total = c.fetchone()[0]
print(f"Total entries: {total}")

conn.close()