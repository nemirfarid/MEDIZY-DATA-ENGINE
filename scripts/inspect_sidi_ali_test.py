import pandas as pd

df = pd.read_excel('C:/Users/pc lenovo/Downloads/Sante_DZ_Google_Maps_Sidi_Ali_test.xlsx')
for idx, r in df.iterrows():
    print(dict(r))

