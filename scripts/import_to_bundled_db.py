import math
import os
import sqlite3
import pandas as pd

CSV_PATH = os.path.expanduser(r'~\Downloads\Annuaire_Sanitaire_Medizy_Consolide_GPS.csv')
DB_PATH = r'assets\data\sante_dz_bundled.db'

print(f"Chargement du CSV consolidé : {CSV_PATH}")
df = pd.read_csv(CSV_PATH, sep=';', encoding='utf-8-sig')
print(f"Total fiches dans CSV : {len(df)}")

# Connexion SQLite
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Vider les tables actuelles
print("Nettoyage des tables SQLite existantes...")
c.execute("DROP TABLE IF EXISTS facilities_fts")
c.execute("DROP TABLE IF EXISTS facilities")
c.execute("DROP TABLE IF EXISTS structures")

# Recréation table structures
c.execute("""
CREATE TABLE structures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_wilaya TEXT NOT NULL,
    nom_wilaya TEXT NOT NULL,
    nom_daira TEXT,
    nom_commune TEXT,
    categorie TEXT NOT NULL,
    discipline_specialite TEXT,
    nom_etablissement_praticien TEXT NOT NULL,
    adresse TEXT,
    telephone TEXT,
    horaires TEXT,
    latitude REAL,
    longitude REAL,
    coordonnees_gps TEXT,
    statut_remarques TEXT,
    source_csv TEXT,
    is_verified INTEGER DEFAULT 0,
    imported_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# Recréation table facilities
c.execute("""
CREATE TABLE facilities (
    id INTEGER PRIMARY KEY,
    nom TEXT,
    categorie TEXT,
    wilaya TEXT,
    wilaya_code TEXT,
    commune TEXT,
    telephone TEXT,
    latitude REAL,
    longitude REAL,
    adresse TEXT
)
""")

# Recréation FTS5 pour recherche textuelle ultra-rapide
c.execute("""
CREATE VIRTUAL TABLE facilities_fts USING fts5(
    nom,
    categorie,
    wilaya,
    commune,
    telephone,
    latitude UNINDEXED,
    longitude UNINDEXED,
    content='facilities',
    content_rowid='id'
)
""")

print("Insertion des données dans 'structures'...")
structures_data = []
facilities_data = []
fts_data = []

for idx, row in df.iterrows():
    f_id = int(row['id'])
    wcode = str(row['code_wilaya']).zfill(2)
    wname = str(row['nom_wilaya']) if pd.notna(row['nom_wilaya']) else ""
    daira = str(row['nom_daira']) if pd.notna(row['nom_daira']) else ""
    commune = str(row['nom_commune']) if pd.notna(row['nom_commune']) else ""
    cat = str(row['categorie']) if pd.notna(row['categorie']) else "Santé"
    disc = str(row['discipline_specialite']) if pd.notna(row['discipline_specialite']) else ""
    nom = str(row['nom_etablissement_praticien']) if pd.notna(row['nom_etablissement_praticien']) else "Établissement Sanitaire"
    addr = str(row['adresse']) if pd.notna(row['adresse']) else ""
    tel = str(row['telephone']) if pd.notna(row['telephone']) else ""
    horaires = str(row['horaires']) if pd.notna(row['horaires']) else "24h/24"
    lat = float(row['latitude'])
    lon = float(row['longitude'])
    gps = str(row['coordonnees_gps']) if pd.notna(row['coordonnees_gps']) else f"{lat:.4f}, {lon:.4f}"
    statut = str(row['statut_remarques']) if pd.notna(row['statut_remarques']) else ""
    source = str(row['source']) if pd.notna(row['source']) else "Medizy"

    structures_data.append((
        f_id, wcode, wname, daira, commune, cat, disc, nom,
        addr, tel, horaires, lat, lon, gps, statut, source, 1
    ))

    facilities_data.append((
        f_id, nom, cat, wname, wcode, commune, tel, lat, lon, addr
    ))

    fts_data.append((
        f_id, nom, cat, wname, commune, tel, lat, lon
    ))

c.executemany("""
INSERT INTO structures (
    id, code_wilaya, nom_wilaya, nom_daira, nom_commune, categorie,
    discipline_specialite, nom_etablissement_praticien, adresse, telephone,
    horaires, latitude, longitude, coordonnees_gps, statut_remarques,
    source_csv, is_verified
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", structures_data)

print("Insertion des données dans 'facilities'...")
c.executemany("""
INSERT INTO facilities (
    id, nom, categorie, wilaya, wilaya_code, commune, telephone,
    latitude, longitude, adresse
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", facilities_data)

print("Alimentation de l'index FTS5...")
c.executemany("""
INSERT INTO facilities_fts (
    rowid, nom, categorie, wilaya, commune, telephone, latitude, longitude
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", fts_data)

print("Création des index d'optimisation...")
c.execute("CREATE INDEX idx_structures_code_wilaya ON structures(code_wilaya)")
c.execute("CREATE INDEX idx_structures_nom_wilaya ON structures(nom_wilaya)")
c.execute("CREATE INDEX idx_structures_nom_commune ON structures(nom_commune)")
c.execute("CREATE INDEX idx_structures_categorie ON structures(categorie)")
c.execute("CREATE INDEX idx_structures_discipline ON structures(discipline_specialite)")
c.execute("CREATE INDEX idx_structures_lat_lon ON structures(latitude, longitude)")
c.execute("CREATE INDEX idx_structures_wilaya_cat ON structures(code_wilaya, categorie)")

c.execute("CREATE INDEX idx_facilities_wilaya_code ON facilities(wilaya_code)")
c.execute("CREATE INDEX idx_facilities_cat ON facilities(categorie)")
c.execute("CREATE INDEX idx_facilities_lat_lon ON facilities(latitude, longitude)")

conn.commit()

# Optimisation VACUUM
print("Optimisation de la base SQLite (VACUUM & ANALYZE)...")
c.execute("ANALYZE")
conn.commit()
conn.close()

# Reconnexion pour vacuum
conn2 = sqlite3.connect(DB_PATH)
conn2.execute("VACUUM")
conn2.close()

print(f"Succès ! La base {DB_PATH} a été mise à jour avec {len(df)} fiches 100% géolocalisées.")

