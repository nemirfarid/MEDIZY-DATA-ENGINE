#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Script d'Import CSV Maître en Masse (Bulk Import)
======================================================================
Charge le fichier Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv
(41 421 lignes, séparateur ';', encodage UTF-8-BOM) dans la table `structures`
via psycopg2 copy_from / executemany SQLite selon l'environnement disponible.

USAGE :
  python -m medizy_pipeline.sql.import_annuaire_csv \
         --csv /chemin/vers/Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv \
         [--db postgresql://user:pass@localhost/medizy] \
         [--batch-size 500] \
         [--dry-run]

ENVIRONNEMENT :
  DATABASE_URL   - URL PostgreSQL (prioritaire sur --db)
  SQLITE_DB_PATH - Chemin SQLite (fallback si pas de PostgreSQL)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterator, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("medizy.import_csv")

# ─────────────────────────────────────────────────────────────────────────────
# Colonnes CSV attendues (dans l'ordre du fichier)
# ─────────────────────────────────────────────────────────────────────────────
CSV_COLUMNS = [
    "id",
    "code_wilaya",
    "nom_wilaya",
    "nom_daira",
    "nom_commune",
    "categorie",
    "discipline_specialite",
    "nom_etablissement_praticien",
    "adresse",
    "telephone",
    "horaires",
    "latitude",
    "longitude",
    "coordonnees_gps",
    "statut_remarques",
    "source",
]

# Colonnes mappées en base (renomme 'source' -> 'source_csv' pour éviter collision)
DB_COLUMNS = [
    "code_wilaya",
    "nom_wilaya",
    "nom_daira",
    "nom_commune",
    "categorie",
    "discipline_specialite",
    "nom_etablissement_praticien",
    "adresse",
    "telephone",
    "horaires",
    "latitude",
    "longitude",
    "coordonnees_gps",
    "statut_remarques",
    "source_csv",
    "geom",          # calculé à la volée depuis lat/lon
]


# ─────────────────────────────────────────────────────────────────────────────
# Nettoyage et normalisation d'une ligne CSV
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class StructureRow:
    code_wilaya: str
    nom_wilaya: str
    nom_daira: str
    nom_commune: str
    categorie: str
    discipline_specialite: str
    nom_etablissement_praticien: str
    adresse: str
    telephone: str
    horaires: str
    latitude: Optional[float]
    longitude: Optional[float]
    coordonnees_gps: str
    statut_remarques: str
    source_csv: str


def _parse_float(val: str) -> Optional[float]:
    """Parse un nombre flottant ; retourne None en cas d'échec."""
    if not val or val.strip() in ("", "N/A", "-", "None"):
        return None
    val = val.strip().replace(",", ".")
    try:
        f = float(val)
        return f if -180 <= f <= 180 else None
    except ValueError:
        return None


def _clean(val: str) -> str:
    """Nettoyage minimal : strip + normalisation des espaces doubles."""
    return " ".join(val.strip().split()) if val else ""


def parse_row(raw: dict) -> Optional[StructureRow]:
    """
    Transforme une ligne brute du lecteur CSV en StructureRow validée.
    Retourne None si la ligne est invalide (nom vide, code_wilaya absent).
    """
    nom = _clean(raw.get("nom_etablissement_praticien", ""))
    code = _clean(raw.get("code_wilaya", "")).zfill(2)

    if not nom or not code or not code.isdigit():
        return None  # Ligne invalide ignorée

    lat = _parse_float(raw.get("latitude", ""))
    lon = _parse_float(raw.get("longitude", ""))

    # Validation plausibilité coordonnées Algérie (BBox approximative)
    if lat is not None and not (18.0 <= lat <= 38.5):
        lat = None
    if lon is not None and not (-9.5 <= lon <= 13.0):
        lon = None

    # Si un seul des deux est invalide, on supprime l'autre
    if lat is None or lon is None:
        lat = lon = None

    return StructureRow(
        code_wilaya=code,
        nom_wilaya=_clean(raw.get("nom_wilaya", "")),
        nom_daira=_clean(raw.get("nom_daira", "")),
        nom_commune=_clean(raw.get("nom_commune", "")),
        categorie=_clean(raw.get("categorie", "")) or "Autre",
        discipline_specialite=_clean(raw.get("discipline_specialite", "")),
        nom_etablissement_praticien=nom,
        adresse=_clean(raw.get("adresse", "")),
        telephone=_clean(raw.get("telephone", "")),
        horaires=_clean(raw.get("horaires", "")),
        latitude=lat,
        longitude=lon,
        coordonnees_gps=_clean(raw.get("coordonnees_gps", "")),
        statut_remarques=_clean(raw.get("statut_remarques", "")),
        source_csv=_clean(raw.get("source", "CSV Annuaire National")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Lecture du CSV par lots (générateur)
# ─────────────────────────────────────────────────────────────────────────────
def csv_batches(
    csv_path: Path,
    batch_size: int = 500,
) -> Iterator[List[StructureRow]]:
    """
    Lit le CSV par lot de `batch_size` lignes.
    Gère l'encodage UTF-8-BOM (utf-8-sig) et le séparateur ';'.
    """
    skipped = 0
    batch: List[StructureRow] = []

    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")

        # Vérification des colonnes
        available = set(reader.fieldnames or [])
        required = {"nom_etablissement_praticien", "code_wilaya"}
        missing = required - available
        if missing:
            raise ValueError(
                f"Colonnes manquantes dans le CSV : {missing}\n"
                f"Colonnes disponibles : {available}"
            )

        for raw in reader:
            row = parse_row(raw)
            if row is None:
                skipped += 1
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []

    if batch:
        yield batch

    if skipped:
        log.warning(f"{skipped} lignes ignorées (invalides ou sans nom/code wilaya).")


# ─────────────────────────────────────────────────────────────────────────────
# Import PostgreSQL (psycopg2 — COPY FROM + execute_values)
# ─────────────────────────────────────────────────────────────────────────────
def _geom_wkt(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    """Retourne le WKT POINT pour ST_GeomFromText ou None."""
    if lat is None or lon is None:
        return None
    return f"POINT({lon} {lat})"


def import_postgres(
    csv_path: Path,
    db_url: str,
    batch_size: int = 500,
    dry_run: bool = False,
) -> dict:
    """Import bulk vers PostgreSQL via psycopg2 execute_values (rapide)."""
    try:
        import psycopg2
        from psycopg2.extras import execute_values
    except ImportError:
        raise RuntimeError(
            "psycopg2 non installé. Exécutez : pip install psycopg2-binary"
        )

    INSERT_SQL = """
        INSERT INTO structures (
            code_wilaya, nom_wilaya, nom_daira, nom_commune,
            categorie, discipline_specialite, nom_etablissement_praticien,
            adresse, telephone, horaires,
            latitude, longitude, coordonnees_gps,
            statut_remarques, source_csv, geom
        ) VALUES %s
        ON CONFLICT DO NOTHING
    """

    TEMPLATE = """(
        %(code_wilaya)s, %(nom_wilaya)s, %(nom_daira)s, %(nom_commune)s,
        %(categorie)s, %(discipline_specialite)s, %(nom_etablissement_praticien)s,
        %(adresse)s, %(telephone)s, %(horaires)s,
        %(latitude)s, %(longitude)s, %(coordonnees_gps)s,
        %(statut_remarques)s, %(source_csv)s,
        CASE
            WHEN %(latitude)s IS NOT NULL AND %(longitude)s IS NOT NULL
            THEN ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326)
            ELSE NULL
        END
    )"""

    stats = {"total": 0, "batches": 0, "errors": 0}
    t0 = time.time()

    conn = psycopg2.connect(db_url)
    try:
        with conn:
            with conn.cursor() as cur:
                # Vérification / création de la table
                cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'structures')"
                )
                exists = cur.fetchone()[0]
                if not exists:
                    log.info("Table 'structures' absente → exécution de 002_structures_annuaire_national.sql")
                    sql_path = Path(__file__).parent / "002_structures_annuaire_national.sql"
                    if sql_path.exists():
                        cur.execute(sql_path.read_text(encoding="utf-8"))
                    else:
                        raise FileNotFoundError(
                            f"Script SQL introuvable : {sql_path}\n"
                            "Exécutez d'abord 002_structures_annuaire_national.sql."
                        )

                for batch in csv_batches(csv_path, batch_size):
                    if dry_run:
                        log.info(f"[DRY-RUN] Lot de {len(batch)} lignes non inséré.")
                        stats["total"] += len(batch)
                        stats["batches"] += 1
                        continue

                    records = [
                        {
                            "code_wilaya": r.code_wilaya,
                            "nom_wilaya": r.nom_wilaya,
                            "nom_daira": r.nom_daira,
                            "nom_commune": r.nom_commune,
                            "categorie": r.categorie,
                            "discipline_specialite": r.discipline_specialite,
                            "nom_etablissement_praticien": r.nom_etablissement_praticien,
                            "adresse": r.adresse,
                            "telephone": r.telephone,
                            "horaires": r.horaires,
                            "latitude": r.latitude,
                            "longitude": r.longitude,
                            "coordonnees_gps": r.coordonnees_gps,
                            "statut_remarques": r.statut_remarques,
                            "source_csv": r.source_csv,
                        }
                        for r in batch
                    ]

                    try:
                        execute_values(
                            cur, INSERT_SQL, records,
                            template=TEMPLATE, page_size=batch_size,
                        )
                        stats["total"] += len(batch)
                        stats["batches"] += 1
                        log.info(
                            f"✔ Lot {stats['batches']:4d} | "
                            f"+{len(batch):5d} lignes | "
                            f"Total : {stats['total']:6d} | "
                            f"Durée : {time.time() - t0:.1f}s"
                        )
                    except Exception as e:
                        log.error(f"Erreur lot {stats['batches'] + 1} : {e}")
                        stats["errors"] += 1
                        conn.rollback()

                if not dry_run:
                    # Rafraîchissement des vues matérialisées
                    log.info("Rafraîchissement des vues matérialisées…")
                    cur.execute(
                        "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_structures_par_wilaya"
                    )
                    cur.execute(
                        "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_structures_par_categorie"
                    )
                    log.info("Vues matérialisées rafraîchies.")

    finally:
        conn.close()

    stats["duration_s"] = round(time.time() - t0, 2)
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Import SQLite (fallback local / tests)
# ─────────────────────────────────────────────────────────────────────────────
def import_sqlite(
    csv_path: Path,
    sqlite_path: str,
    batch_size: int = 500,
    dry_run: bool = False,
) -> dict:
    """Import bulk vers SQLite pour les environnements locaux sans PostgreSQL."""
    import sqlite3

    DDL = """
    CREATE TABLE IF NOT EXISTS structures (
        id                           INTEGER PRIMARY KEY AUTOINCREMENT,
        code_wilaya                  TEXT NOT NULL,
        nom_wilaya                   TEXT NOT NULL,
        nom_daira                    TEXT,
        nom_commune                  TEXT,
        categorie                    TEXT NOT NULL,
        discipline_specialite        TEXT,
        nom_etablissement_praticien  TEXT NOT NULL,
        adresse                      TEXT,
        telephone                    TEXT,
        horaires                     TEXT,
        latitude                     REAL,
        longitude                    REAL,
        coordonnees_gps              TEXT,
        statut_remarques             TEXT,
        source_csv                   TEXT,
        is_verified                  INTEGER NOT NULL DEFAULT 0,
        imported_at                  TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at                   TEXT    NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_structures_code_wilaya    ON structures (code_wilaya);
    CREATE INDEX IF NOT EXISTS idx_structures_nom_wilaya     ON structures (nom_wilaya);
    CREATE INDEX IF NOT EXISTS idx_structures_nom_commune    ON structures (nom_commune);
    CREATE INDEX IF NOT EXISTS idx_structures_categorie      ON structures (categorie);
    CREATE INDEX IF NOT EXISTS idx_structures_discipline     ON structures (discipline_specialite);
    CREATE INDEX IF NOT EXISTS idx_structures_wilaya_cat     ON structures (code_wilaya, categorie);
    CREATE INDEX IF NOT EXISTS idx_structures_lat_lon        ON structures (latitude, longitude)
        WHERE latitude IS NOT NULL;
    """

    INSERT_SQL = """
    INSERT INTO structures (
        code_wilaya, nom_wilaya, nom_daira, nom_commune,
        categorie, discipline_specialite, nom_etablissement_praticien,
        adresse, telephone, horaires,
        latitude, longitude, coordonnees_gps,
        statut_remarques, source_csv
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    stats = {"total": 0, "batches": 0, "errors": 0}
    t0 = time.time()

    conn = sqlite3.connect(sqlite_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32768")  # 32 MB cache

    try:
        conn.executescript(DDL)
        conn.commit()

        for batch in csv_batches(csv_path, batch_size):
            if dry_run:
                log.info(f"[DRY-RUN] Lot de {len(batch)} lignes non inséré.")
                stats["total"] += len(batch)
                stats["batches"] += 1
                continue

            records = [
                (
                    r.code_wilaya, r.nom_wilaya, r.nom_daira, r.nom_commune,
                    r.categorie, r.discipline_specialite, r.nom_etablissement_praticien,
                    r.adresse, r.telephone, r.horaires,
                    r.latitude, r.longitude, r.coordonnees_gps,
                    r.statut_remarques, r.source_csv,
                )
                for r in batch
            ]

            try:
                conn.executemany(INSERT_SQL, records)
                conn.commit()
                stats["total"] += len(batch)
                stats["batches"] += 1
                log.info(
                    f"✔ Lot {stats['batches']:4d} | "
                    f"+{len(batch):5d} lignes | "
                    f"Total : {stats['total']:6d} | "
                    f"Durée : {time.time() - t0:.1f}s"
                )
            except Exception as e:
                log.error(f"Erreur lot {stats['batches'] + 1} : {e}")
                conn.rollback()
                stats["errors"] += 1

    finally:
        conn.close()

    stats["duration_s"] = round(time.time() - t0, 2)
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée principal
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import CSV Annuaire Sanitaire National → MEDIZY DB",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Chemin absolu ou relatif vers le fichier CSV maître.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="URL PostgreSQL (prioritaire sur DATABASE_URL env). "
             "Ex : postgresql://medizy:password@localhost:5432/medizy",
    )
    parser.add_argument(
        "--sqlite",
        default=None,
        help="Chemin du fichier SQLite (fallback). "
             "Priorité : --db > DATABASE_URL > --sqlite > SQLITE_DB_PATH.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Taille des lots d'insertion (optimum entre 200 et 1000).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation : lit et valide le CSV sans insérer en base.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    if not csv_path.exists():
        log.error(f"Fichier CSV introuvable : {csv_path}")
        sys.exit(1)

    log.info(f"═══════════════════════════════════════════════════════")
    log.info(f" MEDIZY — Import CSV Annuaire Sanitaire National")
    log.info(f"═══════════════════════════════════════════════════════")
    log.info(f" Fichier  : {csv_path} ({csv_path.stat().st_size / 1024 / 1024:.1f} Mo)")
    log.info(f" Batch    : {args.batch_size} lignes/lot")
    log.info(f" Mode     : {'DRY-RUN (simulation)' if args.dry_run else 'IMPORT RÉEL'}")
    log.info(f"═══════════════════════════════════════════════════════")

    # Sélection du backend de base de données
    db_url = args.db or os.environ.get("DATABASE_URL", "")
    sqlite_path = args.sqlite or os.environ.get(
        "SQLITE_DB_PATH",
        "E:\\medizy_data\\medizy_facilities_local.db"
        if os.path.exists("E:\\")
        else "medizy_facilities_local.db",
    )

    if db_url and db_url.startswith(("postgres://", "postgresql://")):
        log.info(f" Backend  : PostgreSQL ({db_url.split('@')[-1]})")
        stats = import_postgres(csv_path, db_url, args.batch_size, args.dry_run)
    else:
        log.info(f" Backend  : SQLite ({sqlite_path})")
        stats = import_sqlite(csv_path, sqlite_path, args.batch_size, args.dry_run)

    log.info(f"═══════════════════════════════════════════════════════")
    log.info(f" Rapport final :")
    log.info(f"   Lignes importées : {stats['total']:>7,}")
    log.info(f"   Lots traités     : {stats['batches']:>7,}")
    log.info(f"   Erreurs          : {stats.get('errors', 0):>7,}")
    log.info(f"   Durée totale     : {stats.get('duration_s', 0):>7.2f} s")
    log.info(f"═══════════════════════════════════════════════════════")

    if stats.get("errors", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
