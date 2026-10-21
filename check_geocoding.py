import pandas as pd

df = pd.read_csv(r"D:\SANTE_DZ_EXPORTS\geocoding_applied.csv", dtype=str).fillna("")
print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print(df.head(3).to_string())