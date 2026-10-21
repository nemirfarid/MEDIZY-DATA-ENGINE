# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')
from sqlite_prototype import get_connection, init_schema, import_checkpoint_to_sqlite
import csv
from pathlib import Path

db_path = Path(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
if db_path.exists():
    db_path.unlink()

import_checkpoint_to_sqlite(Path(r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'), db_path)

conn = get_connection(db_path)
count_csv = 0
with open(r'D:\SANTE_DZ_EXPORTS\checkpoint.csv', encoding='utf-8-sig', newline='') as f:
    count_csv = sum(1 for _ in csv.DictReader(f))
count_sqlite = conn.execute('SELECT COUNT(*) FROM places').fetchone()[0]
gps_sqlite = conn.execute('SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL').fetchone()[0]
phone_sqlite = conn.execute("SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ''").fetchone()[0]
place_id_sqlite = conn.execute("SELECT COUNT(*) FROM places WHERE place_id IS NOT NULL AND place_id != ''").fetchone()[0]
wilayas_sqlite = conn.execute('SELECT COUNT(DISTINCT wilaya) FROM places').fetchone()[0]
conn.close()

print('CSV rows:', count_csv)
print('SQLite rows:', count_sqlite)
print('Match:', count_csv == count_sqlite)
print('GPS SQLite:', gps_sqlite)
print('Phone SQLite:', phone_sqlite)
print('Place ID SQLite:', place_id_sqlite)
print('Wilayas SQLite:', wilayas_sqlite)
