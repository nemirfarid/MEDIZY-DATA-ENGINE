import pandas as pd

df = pd.read_csv('Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv', sep=';')
sidi_ali = df[df['nom_commune'].str.contains('Sidi Ali', case=False, na=False)]
print("Sample 15 in Sidi Ali:")
print(sidi_ali[['nom_etablissement_praticien', 'categorie', 'discipline_specialite', 'latitude', 'longitude', 'telephone']].head(15).to_string())

