import sqlite3
import pandas as pd

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
df = pd.read_sql_query("SELECT id, wilaya_code, wilaya, commune, nom, latitude, longitude FROM facilities", con)

# Algeria wilaya centroid reference bounds
# Mostaganem should be around lat 35.8 - 36.3, lon 0.0 - 0.6
bad_mosta = df[(df['wilaya'] == 'Mostaganem') & (df['latitude'] < 35.0)]
print(f"Total bad in Mostaganem: {len(bad_mosta)}")
print("Sample bad Mostaganem records:")
print(bad_mosta[['id', 'nom', 'commune', 'latitude', 'longitude']].head(10))

# Check where lat 33.3 and lon 5.7 appears across the whole database
at_33_3 = df[(df['latitude'] >= 33.2) & (df['latitude'] <= 33.4) & (df['longitude'] >= 5.6) & (df['longitude'] <= 5.8)]
print(f"\nTotal records with lat around 33.3 and lon around 5.7 across all DB: {len(at_33_3)}")
print("Wilayas affected by 33.3, 5.7:")
print(at_33_3['wilaya'].value_counts())

