# Exact OLC Plus Code decoder for Algeria / Sidi Ali
# The prefix for Sidi Ali area (lat ~36.10, lon ~0.41 to 0.43) is '7FR8'
# Let's verify:
# '7' -> index 6 -> 6 * 20 = 120 - 90 = +30
# 'F' -> index 9 -> 9 * 1 = +9 -> 39? Wait, let's decode exact OLC alphabet!

ALPHABET = "23456789CFGHJMPQRVWX"

def decode_full(code):
    code = code.upper().replace('+', '')
    lat = -90.0
    lng = -180.0
    lat_res = 20.0
    lng_res = 20.0
    for i in range(0, min(10, len(code)), 2):
        lat += ALPHABET.index(code[i]) * lat_res
        lng += ALPHABET.index(code[i + 1]) * lng_res
        lat_res /= 20.0
        lng_res /= 20.0
    return lat + (lat_res * 20.0) / 2.0, lng + (lng_res * 20.0) / 2.0

# In Algeria, lat ~36, lon ~0.4:
# Lat: 36 + 90 = 126 -> 126 / 20 = 6 ('7'), rem = 6 -> 6 / 1 = 6 ('7')
# Lon: 0.4 + 180 = 180.4 -> 180.4 / 20 = 9 ('F'), rem = 0.4 -> 0.4 / 1 = 0 ('2')
# Prefix: '7F' + '72' or similar. Let's find exact prefix for (36.1012, 0.4145)

target_lat = 36.1012
target_lon = 0.4145

for c1 in ALPHABET:
    for c2 in ALPHABET:
        for c3 in ALPHABET:
            for c4 in ALPHABET:
                test_code = c1 + c2 + c3 + c4 + "3CX72GV" # Clinique gratuit d'état
                lat, lon = decode_full(test_code)
                if abs(lat - target_lat) < 0.05 and abs(lon - target_lon) < 0.05:
                    print(f"MATCH PREFIX: {c1}{c2}{c3}{c4} -> lat: {lat}, lon: {lon}")
                    break

