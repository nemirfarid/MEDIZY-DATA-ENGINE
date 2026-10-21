# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Prototype SQLite
=====================================
Architecture de base de données pour le scraping national.

Tables :
- wilayas
- communes
- places
- categories
- scrape_tasks
- scrape_runs
- dedup_candidates
- data_quality

IMPORTANT :
- Ce prototype est indépendant du checkpoint.csv existant.
- Aucune migration automatique n'est effectuée vers la production.
- Testé sur une copie du checkpoint avant toute utilisation massive.
"""

import sqlite3
from pathlib import Path
from typing import Optional

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "medizy_scraper.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection):
    """Crée les tables si elles n'existent pas."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS wilayas (
            code TEXT PRIMARY KEY,
            nom_fr TEXT NOT NULL,
            nom_ar TEXT,
            latitude REAL,
            longitude REAL
        );

        CREATE TABLE IF NOT EXISTS communes (
            id TEXT PRIMARY KEY,
            wilaya_code TEXT NOT NULL,
            nom_fr TEXT NOT NULL,
            nom_ar TEXT,
            daira TEXT,
            zip_code TEXT,
            latitude REAL,
            longitude REAL,
            FOREIGN KEY (wilaya_code) REFERENCES wilayas(code)
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            nom_fr TEXT NOT NULL,
            categorie_generale TEXT,
            variantes_recherche TEXT
        );

        CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT UNIQUE,
            nom TEXT NOT NULL,
            nom_normalized TEXT,
            adresse TEXT,
            adresse_normalized TEXT,
            telephone TEXT,
            telephone_normalized TEXT,
            telephone_raw TEXT,
            site_web TEXT,
            note TEXT,
            nombre_avis TEXT,
            horaires TEXT,
            latitude REAL,
            longitude REAL,
            google_maps_url TEXT UNIQUE,
            type_google TEXT,
            wilaya TEXT,
            wilaya_normalized TEXT,
            commune TEXT,
            categorie_recherche TEXT,
            source TEXT,
            scrape_date TEXT,
            status TEXT DEFAULT 'active',
            name_status TEXT DEFAULT 'VERIFIED',
            name_source TEXT,
            recovery_date TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS scrape_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wilaya TEXT NOT NULL,
            commune TEXT,
            category TEXT NOT NULL,
            query_variant TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            result_count INTEGER DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            retry_count INTEGER DEFAULT 0,
            error TEXT,
            UNIQUE(wilaya, commune, category, query_variant)
        );

        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT DEFAULT (datetime('now')),
            finished_at TEXT,
            total_tasks INTEGER DEFAULT 0,
            completed_tasks INTEGER DEFAULT 0,
            failed_tasks INTEGER DEFAULT 0,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS dedup_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_a_id INTEGER NOT NULL,
            place_b_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            niveau TEXT NOT NULL,
            raisons TEXT,
            status TEXT DEFAULT 'pending',
            reviewed_at TEXT,
            FOREIGN KEY (place_a_id) REFERENCES places(id),
            FOREIGN KEY (place_b_id) REFERENCES places(id)
        );

        CREATE TABLE IF NOT EXISTS data_quality (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            measured_at TEXT DEFAULT (datetime('now')),
            total_places INTEGER,
            gps_count INTEGER,
            phone_count INTEGER,
            address_count INTEGER,
            website_count INTEGER,
            category_count INTEGER,
            place_id_count INTEGER,
            rating_count INTEGER,
            opening_hours_count INTEGER,
            commune_count INTEGER,
            duplicate_estimate INTEGER,
            wilaya_count INTEGER
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_places_wilaya ON places(wilaya);
        CREATE INDEX IF NOT EXISTS idx_places_commune ON places(commune);
        CREATE INDEX IF NOT EXISTS idx_places_category ON places(categorie_recherche);
        CREATE INDEX IF NOT EXISTS idx_places_place_id ON places(place_id);
        CREATE INDEX IF NOT EXISTS idx_places_phone_norm ON places(telephone_normalized);
        CREATE INDEX IF NOT EXISTS idx_places_latlng ON places(latitude, longitude);
        CREATE INDEX IF NOT EXISTS idx_scrape_tasks_status ON scrape_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_communes_wilaya ON communes(wilaya_code);
    """)


def import_checkpoint_to_sqlite(csv_path: Path, db_path: Optional[Path] = None, exclude_candidates: bool = True):
    """Importe un checkpoint CSV vers SQLite (prototype uniquement).
    
    Args:
        csv_path: Path to checkpoint CSV.
        db_path: Optional DB path override.
        exclude_candidates: If True, skip entries with name_status='CANDIDATE'
            (error artifacts with invalid names from failed fiche enrichment).
    """
    import csv
    conn = get_connection(db_path)
    init_schema(conn)
    cursor = conn.cursor()
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    # Filter out CANDIDATE entries if exclude_candidates is True
    if exclude_candidates:
        original_count = len(rows)
        rows = [r for r in rows if (r.get("name_status", "") or r.get("name_status", "VERIFIED")) != "CANDIDATE"]
        skipped = original_count - len(rows)
        if skipped > 0:
            print(f"Exclusion de {skipped} entrées CANDIDATE (artéfacts d'erreur)")
    print(f"Import de {len(rows)} lignes depuis {csv_path}")
    for r in rows:
        cursor.execute("""
            INSERT OR IGNORE INTO places (
                place_id, nom, nom_normalized, adresse, adresse_normalized,
                telephone, telephone_normalized, telephone_raw, site_web,
                note, nombre_avis, horaires, latitude, longitude,
                google_maps_url, type_google, wilaya, wilaya_normalized,
                commune, categorie_recherche, source, scrape_date,
                name_status, name_source, recovery_date
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            r.get("place_id_si_visible", "").strip() or None,
            r.get("nom", "").strip(),
            r.get("nom", "").strip().lower(),
            r.get("adresse", "").strip(),
            r.get("adresse", "").strip().lower(),
            r.get("telephone", "").strip(),
            None,  # telephone_normalized calculé après
            r.get("telephone", "").strip(),
            r.get("site_web", "").strip(),
            r.get("note", "").strip(),
            r.get("nombre_avis", "").strip(),
            r.get("horaires", "").strip(),
            float(r["latitude"]) if r.get("latitude", "").strip() else None,
            float(r["longitude"]) if r.get("longitude", "").strip() else None,
            r.get("google_maps_url", "").strip(),
            r.get("type_google", "").strip(),
            r.get("wilaya", "").strip(),
            r.get("wilaya", "").strip().lower(),
            r.get("commune", "").strip(),
            r.get("categorie_recherche", "").strip(),
            r.get("source", "").strip(),
            r.get("scrape_date", "").strip(),
            r.get("name_status", "VERIFIED").strip(),
            r.get("name_source", "").strip() or None,
            r.get("recovery_date", "").strip() or None,
        ))
    conn.commit()
    count = cursor.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    print(f"Import terminé. Total dans SQLite : {count}")
    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="initialiser le schéma")
    parser.add_argument("--import-checkpoint", action="store_true", help="importer checkpoint.csv")
    parser.add_argument("--db", default=str(DB_PATH), help="chemin vers la base")
    args = parser.parse_args()
    db_path = Path(args.db)
    if args.init:
        conn = get_connection(db_path)
        init_schema(conn)
        conn.close()
        print(f"Schéma initialisé : {db_path}")
    if args.import_checkpoint:
        import_checkpoint_to_sqlite(Path(r"D:\SANTE_DZ_EXPORTS\checkpoint.csv"), db_path)
