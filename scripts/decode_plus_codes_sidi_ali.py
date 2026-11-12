# Implementation of Google Open Location Code (Plus Codes) in pure Python
CODE_ALPHABET = '23456789CFGHJMPQRVWX'
ENCODING_BASE = len(CODE_ALPHABET)
PAIR_CODE_LENGTH = 10
GRID_CODE_LENGTH = 15

def decode_plus_code(code):
    code = code.replace('+', '').upper()
    lat = 0.0
    lon = 0.0
    lat_val = 0
    lon_val = 0
    
    # decode pairs
    lat_res = 20.0
    lon_res = 20.0
    for i in range(0, min(len(code), 10), 2):
        lat_res /= 20.0
        lon_res /= 20.0
        lat_digit = CODE_ALPHABET.index(code[i])
        lon_digit = CODE_ALPHABET.index(code[i+1])
        lat += lat_digit * lat_res
        lon += lon_digit * lon_res
        
    return lat - 90.0 + lat_res / 2.0, lon - 180.0 + lon_res / 2.0

def recover_nearest(short_code, ref_lat, ref_lon):
    short_code = short_code.upper().replace('+', '')
    # Reference coordinates to full prefix
    # For Sidi Ali (36.1, 0.41):
    # Latitude offset = 36.1 + 90 = 126.1
    # 126.1 / 20 = 6 (CODE_ALPHABET[6] = '7') -> remainder 6.1 -> 6.1 / 1 = 6 ('7') -> 7FR8 or 7FR7...
    # Let's find prefix by testing 4 characters
    best_lat, best_lon = None, None
    min_dist = 999999
    for c1 in CODE_ALPHABET:
        for c2 in CODE_ALPHABET:
            for c3 in CODE_ALPHABET:
                for c4 in CODE_ALPHABET:
                    full_candidate = c1 + c2 + c3 + c4 + short_code
                    lat, lon = decode_plus_code(full_candidate)
                    dist = (lat - ref_lat)**2 + (lon - ref_lon)**2
                    if dist < min_dist:
                        min_dist = dist
                        best_lat, best_lon = lat, lon
                        if dist < 0.01:
                            return best_lat, best_lon
    return best_lat, best_lon

import pandas as pd
import re

df = pd.read_excel('C:/Users/pc lenovo/Downloads/Sante_DZ_Google_Maps_Sidi_Ali_test.xlsx')
print(f"Decoding Plus Codes for {len(df)} facilities in Sidi Ali:")

ref_lat = 36.1012
ref_lon = 0.4145

results = []
for idx, r in df.iterrows():
    name = r['Nom']
    addr = str(r['Adresse'])
    m = re.search(r'([23456789CFGHJMPQRVWX]{4}\+[23456789CFGHJMPQRVWX]{2,})', addr)
    if m:
        short_code = m.group(1)
        lat, lon = recover_nearest(short_code, ref_lat, ref_lon)
        results.append((name, r['Catégorie'], lat, lon, short_code, r['Google Place ID'], r['Téléphone']))
        print(f"  [OK PlusCode] {name}: {short_code} -> ({lat:.6f}, {lon:.6f})")
    else:
        results.append((name, r['Catégorie'], None, None, None, r['Google Place ID'], r['Téléphone']))
        print(f"  [No PlusCode] {name} -> {addr}")

