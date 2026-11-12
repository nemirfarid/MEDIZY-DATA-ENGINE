import pandas as pd

for fname in ['SanteDZ_Mostaganem_GoogleMaps.xlsx', 'Sante_DZ_Google_Maps_Sidi_Ali_test.xlsx']:
    path = f'C:/Users/pc lenovo/Downloads/{fname}'
    try:
        df = pd.read_excel(path)
        print(f"\n--- {fname} ({len(df)} rows) ---")
        print("Columns:", df.columns.tolist())
        print(df.head(10))
    except Exception as e:
        print(f"Error reading {fname}: {e}")

