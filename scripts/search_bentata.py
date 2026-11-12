import pandas as pd
import sqlite3

raw_csv = 'C:/Users/pc lenovo/Downloads/Google Maps Extractor/all-task-1-overview.csv'
df1 = pd.read_csv(raw_csv, low_memory=False)
bentata1 = df1[df1.astype(str).apply(lambda row: row.str.contains('bentata', case=False).any(), axis=1)]
print('Bentata in all-task-1-overview:', len(bentata1))
for _, r in bentata1.iterrows():
    print(' ', r.get('name'), '|', r.get('main_category'), '|', r.get('address'), '|', r.get('link'))

df2 = pd.read_csv('C:/Users/pc lenovo/Downloads/Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv', low_memory=False)
bentata2 = df2[df2.astype(str).apply(lambda row: row.str.contains('bentata', case=False).any(), axis=1)]
print('Bentata in 58_Wilayas_Parfait:', len(bentata2))
for _, r in bentata2.iterrows():
    print(' ', r.get('nom'), '|', r.get('categorie'), '|', r.get('commune'), '|', r.get('wilaya'))

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()
bentata_db = cur.execute("SELECT id, nom, categorie, commune, wilaya, latitude, longitude FROM facilities WHERE nom LIKE '%bentata%' OR adresse LIKE '%bentata%'").fetchall()
print('Bentata in bundled DB:', len(bentata_db))
for r in bentata_db:
    print(' ', r)

