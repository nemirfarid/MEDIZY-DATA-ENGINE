import sqlite3

src_conn = sqlite3.connect('_BACKUP_V1_LEGACY/medizy_scraper.db')
src_c = src_conn.cursor()
src_c.execute("SELECT id, wilaya_code, nom_fr, nom_ar, daira, zip_code, latitude, longitude FROM communes")
all_communes = src_c.fetchall()
print(f"Read {len(all_communes)} communes from medizy_scraper.db")

tgt_conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
tgt_c = tgt_conn.cursor()

tgt_c.execute("DROP TABLE IF EXISTS communes")
tgt_c.execute("""
CREATE TABLE communes (
    id TEXT PRIMARY KEY,
    wilaya_code TEXT NOT NULL,
    nom_fr TEXT NOT NULL,
    nom_ar TEXT,
    daira TEXT,
    zip_code TEXT,
    latitude REAL,
    longitude REAL
);
""")
tgt_c.execute("CREATE INDEX idx_communes_wilaya ON communes(wilaya_code);")
tgt_c.execute("CREATE INDEX idx_communes_nom_fr ON communes(nom_fr);")

tgt_c.executemany("""
INSERT INTO communes (id, wilaya_code, nom_fr, nom_ar, daira, zip_code, latitude, longitude)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", all_communes)

tgt_conn.commit()
print("Successfully inserted 1541 official communes into assets/data/sante_dz_bundled.db")

