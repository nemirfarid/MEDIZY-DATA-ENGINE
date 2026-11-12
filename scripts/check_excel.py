import pandas as pd

df = pd.read_excel('RAPPORT_ALIGNEMENT_MEDIZY_GOOGLE_MAPS_1541_COMMUNES_OFFICIEL.xlsx')
print('Total rows:', len(df))
print('Columns:', list(df.columns))

google_col = 'Nom de la structure ou praticien Google Maps'
mask = (df['Commune'].str.contains('Sidi Ali', case=False, na=False)) & (df[google_col].str.contains('Ainouch|Ouzani|Boussaid|Anis|Lazergui', case=False, na=False))
sidi_ali = df[mask]
print('\n--- Extraits Sidi Ali ---')
for idx, r in sidi_ali.iterrows():
    print(f"* {r[google_col]} | Google GPS: {r['Coordonnées GPS Google Maps']} | Medizy GPS: {r['Coordonnées GPS Medizy']} | Dist: {r['Distance (mètres)']}m | Dist<1m: {r['Distance < 1 mètre']} | Action: {r['Statut / Action Medizy']}")

print('\nDistribution Statut Medizy:')
print(df['Statut / Action Medizy'].value_counts())

print('\nDistribution Distance < 1 metre:')
print(df['Distance < 1 mètre'].value_counts())
