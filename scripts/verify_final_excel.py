import pandas as pd

df = pd.read_excel('RAPPORT_NATIONAL_ALIGNEMENT_1541_COMMUNES_DEFINITIF.xlsx')
print("Total rows:", len(df))
print("\nStatut / Action distribution:")
print(df['Statut / Action Medizy'].value_counts())
print("\nDistance < 1 metre distribution:")
print(df['Distance < 1 mètre'].value_counts())

print("\n--- Échantillon de structures CORRIGÉ (GPS décalé rectifié) ---")
corriges = df[df['Statut / Action Medizy'] == 'CORRIGÉ'].head(10)
for idx, r in corriges.iterrows():
    print(f"* [{r['Wilaya']} - {r['Commune']}] {r['Nom de la structure ou praticien Google Maps']} | Google GPS: {r['Coordonnées GPS Google Maps']} | Medizy GPS: {r['Coordonnées GPS Medizy']} | Ecart initial: {r['Distance (mètres)']}m | Action: {r['Statut / Action Medizy']}")

print("\n--- Échantillon de structures AJOUTÉ & SUPERPOSÉ (absentes sur Medizy créées avec GPS Google) ---")
ajoutes = df[df['Statut / Action Medizy'] == 'AJOUTÉ & SUPERPOSÉ'].head(5)
for idx, r in ajoutes.iterrows():
    print(f"* [{r['Wilaya']} - {r['Commune']}] {r['Nom de la structure ou praticien Google Maps']} | GPS: {r['Coordonnées GPS Google Maps']} | Action: {r['Statut / Action Medizy']}")

