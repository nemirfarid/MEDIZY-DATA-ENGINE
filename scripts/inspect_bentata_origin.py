import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
c.execute("SELECT id, place_id, nom, latitude, longitude, adresse, source FROM facilities WHERE id = 15414")
row = c.fetchone()
print("Record 15414:", row)

# Let's search raw CSV for "Tata" or "Ben Tata" or "Pediatre" in Mostaganem/Sidi Ali
import pandas as pd
df = pd.read_csv('C:/Users/pc lenovo/Downloads/Google Maps Extractor/all-task-1-overview.csv', low_memory=False)
matches = df[df['name'].str.contains('tata', case=False, na=False) | df['name'].str.contains('bentata', case=False, na=False)]
print(f"Matches in CSV for tata/bentata: {len(matches)}")
for idx, r in matches.iterrows():
    print("  CSV match:", r['name'], r['place_id'], r['link'])

conn.close()

