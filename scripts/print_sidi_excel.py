import pandas as pd

df = pd.read_excel('C:/Users/pc lenovo/Downloads/Sante_DZ_Google_Maps_Sidi_Ali_test.xlsx')
for idx, r in df.iterrows():
    name = r['Nom']
    cat = r['Catégorie']
    addr = r['Adresse']
    phone = r['Téléphone']
    pid = r['Google Place ID']
    print(f"{idx+1}. {name} | {cat} | {addr} | Phone: {phone} | PlaceID: {pid}")

