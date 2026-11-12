import pandas as pd

df = pd.read_csv('Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv', sep=';', nrows=5)
print("CSV columns:", df.columns.tolist())

df_full = pd.read_csv('Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv', sep=';', usecols=['nom_wilaya', 'nom_commune', 'nom_etablissement_praticien'])
print("Total rows in CSV:", len(df_full))
print("Distinct wilayas:", df_full['nom_wilaya'].nunique())
print("Distinct communes:", df_full['nom_commune'].nunique())

# Check Ainouch / Boussaid / Ouzani in this CSV
print("Ainouch in CSV:", df_full[df_full['nom_etablissement_praticien'].str.contains('Ainouch|عاينوش', case=False, na=False)][['nom_wilaya', 'nom_commune', 'nom_etablissement_praticien']])
print("Sidi Ali count in CSV:", len(df_full[df_full['nom_commune'].str.contains('Sidi Ali', case=False, na=False)]))

