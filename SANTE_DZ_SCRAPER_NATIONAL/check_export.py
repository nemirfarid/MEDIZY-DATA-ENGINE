import pandas as pd
xls = pd.ExcelFile(r'D:\SANTE_DZ_EXPORTS\SANTE_DZ_GOOGLE_MAPS_NATIONAL_FINAL.xlsx')
print('Sheets:', xls.sheet_names)
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)
    print(f'Sheet "{sheet}": {len(df)} rows')
    print(f'  Columns: {list(df.columns)}')
    if len(df) > 0:
        print(f'  Sample: {df.head(2).to_dict()}')
    print()