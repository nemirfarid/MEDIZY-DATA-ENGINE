import pandas as pd

df = pd.read_csv('Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv', nrows=5)
print("CSV columns:", df.columns.tolist())
print(df.head(2).to_dict(orient='records'))

# Check row count
df_full = pd.read_csv('Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv', usecols=['nom_wilaya', 'nom_commune'])
print("Total rows in CSV:", len(df_full))
print("Distinct wilayas:", df_full['nom_wilaya'].nunique())
print("Distinct communes:", df_full['nom_commune'].nunique())

