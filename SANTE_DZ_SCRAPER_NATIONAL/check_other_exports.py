import pandas as pd
xls = pd.ExcelFile(r'D:\SANTE_DZ_EXPORTS\SANTE_DZ_GOOGLE_MAPS_NATIONAL.xlsx')
print('Sheets:', xls.sheet_names)
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)
    print(f'Sheet "{sheet}": {len(df)} rows')
    print(f'  Columns: {list(df.columns)}')
print()

xls2 = pd.ExcelFile(r'D:\SANTE_DZ_EXPORTS\MEDIZY_NATIONAL.xlsx')
print('MEDIZY Sheets:', xls2.sheet_names)
for sheet in xls2.sheet_names:
    df = pd.read_excel(xls2, sheet_name=sheet)
    print(f'Sheet "{sheet}": {len(df)} rows')
    print(f'  Columns: {list(df.columns)}')