import pandas as pd

try:
    df = pd.read_excel('RAPPORT_NATIONAL_ALIGNEMENT_1541_COMMUNES_DEFINITIF.xlsx')
    print("=== Row 25390 to 25400 of RAPPORT_NATIONAL_ALIGNEMENT_1541_COMMUNES_DEFINITIF.xlsx ===")
    print(df.iloc[25390:25402][['Wilaya', 'Commune', 'Nom de la structure ou praticien Google Maps', 'Coordonnées GPS Google Maps', 'Nom de la structure Medizy', 'Coordonnées GPS Medizy', 'Distance (mètres)', 'Distance < 1 mètre', 'Statut / Action Medizy']].to_string())
except Exception as e:
    print("Error:", e)

