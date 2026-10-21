import pandas as pd
xls = pd.ExcelFile(r'D:\SANTE_DZ_EXPORTS\SCRAPING_NATIONAL_STATUS.xlsx')
print('Sheets:', xls.sheet_names)
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)
    print(f'Sheet "{sheet}": {len(df)} rows')
    print(f'  Columns: {list(df.columns)}')
    if len(df) < 50:
        print(df.to_string())
    else:
        print(df.head(10).to_string())
    print()