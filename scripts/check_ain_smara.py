import pandas as pd

df = pd.read_excel('RAPPORT_ALIGNEMENT_MEDIZY_GOOGLE_MAPS_1541_COMMUNES_OFFICIEL.xlsx')
print(df.iloc[22550:22565][['Wilaya', 'Commune', 'Nom de la structure ou praticien Google Maps', 'Coordonnées GPS Google Maps', 'Nom de la structure Medizy', 'Coordonnées GPS Medizy', 'Distance (mètres)', 'Distance < 1 mètre', 'Statut / Action Medizy']].to_string())

