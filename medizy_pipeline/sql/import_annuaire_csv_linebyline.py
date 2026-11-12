#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Script d'Import CSV Maître (Ligne par Ligne)
==================================================================
Lit le fichier Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv
(41 421+ lignes, séparateur ';', encodage UTF-8-BOM) et insère
chaque ligne individuellement dans la base SQLite, avec journalisation
stricte des erreurs et rapport final précis.

USAGE :
  python -m medizy_pipeline.sql.import_annuaire_csv_linebyline \
         --csv /chemin/vers/Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv \
         [--db /chemin/vers/sante_dz_bundled.db] \
         [--batch-size 10] \
         [--error-log import_errors.log]

ENVIRONNEMENT :
  SQLITE_DB_PATH - Chemin SQLite (par défaut: assets/data/sante_dz_bundled.db)
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("medizy.import_csv_linebyline")

CSV_COLUMNS = [
    "id", "code_wilaya", "nom_wilaya", "nom_daira", "nom_commune",
    "categorie", "discipline_specialite", "nom_etablissement_praticien",
    "adresse", "telephone", "horaires", "latitude", "longitude",
    "coordonnees_gps", "statut_remarques", "source",
]

DB_COLUMNS = [
    "code_wilaya", "nom_wilaya", "nom_daira", "nom_commune", "categorie",
    "discipline_specialite", "nom_etablissement_praticien", "adresse",
    "telephone", "horaires", "latitude", "longitude", "coordonnees_gps",
    "statut_remarques", "source_csv",
]


def _parse_float(val: str) -> Optional[float]:
    if not val or val.strip() in ("", "N/A", "-", "None", "null", "NULL"):
        return None
    val = val.strip().replace(",", ".")
    try:
        f = float(val)
        return f if -180 <= f <= 180 else None
    except ValueError:
        return None


def _clean(val: str) -> str:
    return " ".join(val.strip().split()) if val else ""


def validate_row(raw: dict, line_num: int) -> tuple:
    """
    Valide et nettoie une ligne CSV.
    Retourne (row_dict, error_message).
    Si error_message est None, la ligne est valide.
    """
    nom = _clean(raw.get("nom_etablissement_praticien", ""))
    code = _clean(raw.get("code_wilaya", "")).zfill(2)

    if not nom:
        return None, f"Ligne {line_num}: nom_etablissement_praticien vide"
    if not code or not code.isdigit():
        return None, f"Ligne {line_num}: code_wilaya invalide ('{code}')"

    lat = _parse_float(raw.get("latitude", ""))
    lon = _parse_float(raw.get("longitude", ""))

    # Validation BBox Algérie
    if lat is not None and not (18.0 <= lat <= 38.5):
        lat = None
    if lon is not None and not (-9.5 <= lon <= 13.0):
        lon = None
    if lat is None or lon is None:
        lat = lon = None

    row = {
        "code_wilaya": code,
        "nom_wilaya": _clean(raw.get("nom_wilaya", "")),
        "nom_daira": _clean(raw.get("nom_daira", "")),
        "nom_commune": _clean(raw.get("nom_commune", "")),
        "categorie": _clean(raw.get("categorie", "")) or "Autre",
        "discipline_specialite": _clean(raw.get("discipline_specialite", "")),
        "nom_etablissement_praticien": nom,
        "adresse": _clean(raw.get("adresse", "")),
        "telephone": _clean(raw.get("telephone", "")),
        "horaires": _clean(raw.get("horaires", "")),
        "latitude": lat,
        "longitude": lon,
        "coordonnees_gps": _clean(raw.get("coordonnees_gps", "")),
        "statut_remarques": _clean(raw.get("statut_remarques", "")),
        "source_csv": _clean(raw.get("source", "CSV Annuaire National")),
    }
    return row, None


def import_line_by_line(csv_path: Path, db_path: Path, batch_size: int, error_log_path: Path):
    """Import ligne par ligne avec journalisation stricte."""
    total_lines = 0
    inserted = 0
    errors = []
    error_file = open(error_log_path, "w", encoding="utf-8")

    # Supprimer l'ancienne base et recréer
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    # Créer la table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS structures (
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
    conn.commit()

    t0 = time.time()

    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        available = set(reader.fieldnames or [])
        required = {"nom_etablissement_praticien", "code_wilaya"}
        missing = required - available
        if missing:
            raise ValueError(f"Colonnes manquantes : {missing}")

        for raw in reader:
            total_lines += 1
            line_num = total_lines + 1  # +1 pour l'en-tête

            row, err = validate_row(raw, line_num)
            if err:
                errors.append(err)
                error_file.write(f"{err}\n")
                continue

            try:
                conn.execute(
                    """INSERT INTO structures (
                        code_wilaya, nom_wilaya, nom_daira, nom_commune, categorie,
                        discipline_specialite, nom_etablissement_praticien, adresse,
                        telephone, horaires, latitude, longitude, coordonnees_gps,
                        statut_remarques, source_csv
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        row["code_wilaya"], row["nom_wilaya"], row["nom_daira"],
                        row["nom_commune"], row["categorie"], row["discipline_specialite"],
                        row["nom_etablissement_praticien"], row["adresse"],
                        row["telephone"], row["horaires"], row["latitude"],
                        row["longitude"], row["coordonnees_gps"], row["statut_remarques"],
                        row["source_csv"],
                    ),
                )
                inserted += 1

                # Mini-lot transactionnel : commit toutes les N lignes
                if inserted % batch_size == 0:
                    conn.commit()
                    log.info(f"Lot {inserted // batch_size} | +{batch_size} lignes | Total: {inserted}")

            except Exception as e:
                errors.append(f"Ligne {line_num}: {e}")
                error_file.write(f"Ligne {line_num}: {e}\n")
                conn.rollback()

    # Commit final
    conn.commit()

    # Créer les index
    log.info("Création des index...")
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_structures_code_wilaya ON structures(code_wilaya);",
        "CREATE INDEX IF NOT EXISTS idx_structures_nom_wilaya ON structures(nom_wilaya);",
        "CREATE INDEX IF NOT EXISTS idx_structures_nom_commune ON structures(nom_commune);",
        "CREATE INDEX IF NOT EXISTS idx_structures_categorie ON structures(categorie);",
        "CREATE INDEX IF NOT EXISTS idx_structures_discipline ON structures(discipline_specialite);",
        "CREATE INDEX IF NOT EXISTS idx_structures_lat_lon ON structures(latitude, longitude);",
        "CREATE INDEX IF NOT EXISTS idx_structures_wilaya_cat ON structures(code_wilaya, categorie);",
    ]:
        conn.execute(idx_sql)
    conn.commit()

    # Créer la table facilities (alias pour compatibilité Dart)
    log.info("Création de la table facilities (alias)...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facilities (
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
    conn.execute("""
        INSERT INTO facilities (id, nom, categorie, wilaya, wilaya_code, commune, telephone, latitude, longitude, adresse)
        SELECT id, nom_etablissement_praticien, categorie, nom_wilaya, code_wilaya, nom_commune, telephone, latitude, longitude, adresse FROM structures
    """)
    conn.commit()

    # Créer la table FTS5 pour la recherche textuelle
    log.info("Création de la table FTS5...")
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS facilities_fts USING fts5(nom, categorie, wilaya, commune, telephone, latitude, longitude)")
    conn.execute("""INSERT INTO facilities_fts (rowid, nom, categorie, wilaya, commune, telephone, latitude, longitude)
        SELECT id, nom, categorie, wilaya, commune, telephone, latitude, longitude FROM facilities""")
    conn.commit()

    conn.close()
    error_file.close()

    elapsed = time.time() - t0

    # Rapport final
    print("\n" + "=" * 60)
    print("  RAPPORT D'IMPORTATION FINALE")
    print("=" * 60)
    print(f"  Lignes lues dans le CSV   : {total_lines:,}")
    print(f"  Lignes insérées avec succès : {inserted:,}")
    print(f"  Lignes en erreur           : {len(errors)}")
    print(f"  Durée totale               : {elapsed:.2f}s")
    print("=" * 60)

    if errors:
        print(f"\n  Détail des erreurs ({len(errors)}):")
        for e in errors[:20]:
            print(f"    - {e}")
        if len(errors) > 20:
            print(f"    ... et {len(errors) - 20} autres erreurs (voir {error_log_path})")
    else:
        print("\n  ✅ Aucune erreur — 100% des lignes importées avec succès !")

    print(f"\n  Journal d'erreurs : {error_log_path}")
    print(f"  Base SQLite      : {db_path}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Import CSV ligne par ligne dans SQLite")
    parser.add_argument("--csv", required=True, help="Chemin du fichier CSV")
    parser.add_argument("--db", default=None, help="Chemin de la base SQLite")
    parser.add_argument("--batch-size", type=int, default=10, help="Taille des mini-lots (défaut: 10)")
    parser.add_argument("--error-log", default="import_errors.log", help="Fichier de log des erreurs")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        log.error(f"Fichier CSV introuvable : {csv_path}")
        return 1

    db_path = Path(args.db) if args.db else Path(os.environ.get("SQLITE_DB_PATH", "assets/data/sante_dz_bundled.db"))
    error_log_path = Path(args.error_log)

    log.info(f"CSV : {csv_path}")
    log.info(f"DB  : {db_path}")
    log.info(f"Batch size : {args.batch_size}")
    log.info(f"Error log  : {error_log_path}")

    import_line_by_line(csv_path, db_path, args.batch_size, error_log_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
