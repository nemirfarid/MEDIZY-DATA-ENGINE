import pandas as pd

try:
    df = pd.read_csv('C:/Users/pc lenovo/Downloads/Google Maps Extractor/all-task-1-overview.csv', low_memory=False)
    print("Total rows:", len(df))
    # Filter for Sidi Ali
    sidi = df[df['title'].str.contains('Sidi Ali', case=False, na=False) | 
              df['city'].str.contains('Sidi Ali', case=False, na=False) | 
              df['address'].str.contains('Sidi Ali', case=False, na=False)]
    print("Found matching Sidi Ali in Extractor CSV:", len(sidi))
    for _, r in sidi.iterrows():
        print(f"Title: {r.get('title')}, City: {r.get('city')}, Lat: {r.get('latitude')}, Lon: {r.get('longitude')}, Cat: {r.get('categoryName')}")
except Exception as e:
    print("Error:", e)

