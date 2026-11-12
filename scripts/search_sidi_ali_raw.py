import pandas as pd

df = pd.read_csv('C:/Users/pc lenovo/Downloads/Google Maps Extractor/all-task-1-overview.csv', low_memory=False)
mask = df['name'].str.contains('Sidi Ali', case=False, na=False) | df['address'].str.contains('Sidi Ali', case=False, na=False)
sidi = df[mask]
print("Found in extractor for Sidi Ali:", len(sidi))
for _, r in sidi.iterrows():
    print(f"Name: {r['name']}, Category: {r.get('main_category')}, Address: {r.get('address')}, Link: {r.get('link')}")

