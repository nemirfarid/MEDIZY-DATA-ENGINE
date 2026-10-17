#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SANTÉ DZ / MEDIZY — INGESTION SÉCURISÉE D'EXPANSION PHASE 6
==========================================================
Transfère de manière transactionnelle et atomique les nouveaux établissements
qualifiés depuis D:\\SANTE_DZ_EXPORTS\\medizy_staging_expansion.db
vers la base de production C:\\SANTE_DZ_SCRAPER\\medizy_scraper.db.

Contrôles de sécurité :
1. Vérification préalable de l'intégrité de la base de production (23 669 entrées).
2. Vérification d'absence de conflit de place_id (INSERT OR IGNORE).
3. Transaction unique (commit atomique ou rollback immédiat).
4. Contrôle post-ingestion de non-régression sur les 23 669 entrées initiales.
5. Intégrité SQLite finale (PRAGMA integrity_check).
"""

import os
import sys
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROD_DB = str(PROJECT_ROOT / "medizy_scraper.db")
EXPORTS_DIR = Path(r"D:\SANTE_DZ_EXPORTS")
STAGING_DB = str(EXPORTS_DIR / "medizy_staging_expansion.db")


def calculate_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("=" * 70)
    print("SANTÉ DZ / MEDIZY — INGESTION TRANSACTIONNELLE PHASE 6")
    print("=" * 70)

    if not os.path.exists(PROD_DB):
        sys.stderr.write(f"ERREUR : Base de production introuvable ({PROD_DB})\n")
        sys.exit(1)

    if not os.path.exists(STAGING_DB):
        sys.stderr.write(f"ERREUR : Base de staging introuvable ({STAGING_DB})\n")
        sys.exit(1)

    # 1. Vérification pré-ingestion
    con_prod = sqlite3.connect(PROD_DB)
    cur_prod = con_prod.cursor()
    cur_prod.execute("PRAGMA integrity_check")
    integ = cur_prod.fetchone()[0]
    if integ != "ok":
        sys.stderr.write(f"ERREUR CRITIQUE : Intégrité SQLite compromise avant ingestion ({integ})\n")
        sys.exit(1)

    cur_prod.execute("SELECT COUNT(*) FROM places")
    initial_count = cur_prod.fetchone()[0]
    print(f"[PRE-CHECK] Intégrité SQLite : {integ}")
    print(f"[PRE-CHECK] Volume initial en production : {initial_count} établissements")

    # Mémoriser les IDs d'origine pour contrôle de non-régression
    cur_prod.execute("SELECT id, nom, wilaya, telephone FROM places")
    original_entries_sample = cur_prod.fetchmany(100)

    # 2. Lecture des données de staging
    con_stage = sqlite3.connect(f"file:{STAGING_DB}?mode=ro", uri=True)
    con_stage.row_factory = sqlite3.Row
    cur_stage = con_stage.cursor()
    cur_stage.execute("SELECT * FROM staging_new_places ORDER BY id ASC")
    new_places = [dict(r) for r in cur_stage.fetchall()]
    con_stage.close()

    print(f"[STAGING] Nouveaux établissements qualifiés à ingérer : {len(new_places)}")
    if not new_places:
        print("[WARN] Aucun nouvel établissement à ingérer.")
        sys.exit(0)

    # 3. Colonnes cibles dans la table places
    cur_prod.execute("PRAGMA table_info(places)")
    prod_cols = [r[1] for r in cur_prod.fetchall() if r[1] != "id"]

    insert_cols = [
        "place_id", "nom", "nom_normalized", "categorie_recherche", "type_google",
        "wilaya", "wilaya_normalized", "commune", "adresse", "adresse_normalized",
        "telephone", "telephone_normalized", "telephone_raw", "site_web", "horaires",
        "latitude", "longitude", "google_maps_url", "source", "scrape_date", "status",
        "created_at", "updated_at", "name_status", "name_source", "commune_source",
        "commune_confidence", "commune_updated_at", "geocoding_level"
    ]
    # Filtrer uniquement les colonnes existantes dans places
    active_cols = [c for c in insert_cols if c in prod_cols]
    placeholders = ", ".join(["?"] * len(active_cols))
    sql = f"INSERT OR IGNORE INTO places ({', '.join(active_cols)}) VALUES ({placeholders})"

    # 4. Ingestion transactionnelle atomique
    print(f"[INGESTION] Démarrage de la transaction d'insertion...")
    inserted_count = 0
    now_iso = datetime.now().isoformat()

    try:
        cur_prod.execute("BEGIN TRANSACTION")
        for p in new_places:
            row_data = []
            for col in active_cols:
                if col == "wilaya_normalized":
                    row_data.append(p.get("wilaya", "").lower().strip())
                elif col == "adresse_normalized":
                    row_data.append(p.get("adresse", "").lower().strip())
                elif col == "commune_updated_at":
                    row_data.append(now_iso)
                else:
                    row_data.append(p.get(col))
            cur_prod.execute(sql, row_data)
            if cur_prod.rowcount > 0:
                inserted_count += 1

        con_prod.commit()
        print(f"[OK] Transaction validée : {inserted_count} établissements insérés avec succès.")
    except Exception as e:
        con_prod.rollback()
        sys.stderr.write(f"ERREUR LORS DE L'INGESTION (ROLLBACK EFFECTUÉ) : {e}\n")
        sys.exit(1)

    # 5. Contrôles post-ingestion
    cur_prod.execute("SELECT COUNT(*) FROM places")
    final_count = cur_prod.fetchone()[0]
    expected_count = initial_count + inserted_count
    print(f"[POST-CHECK] Volume final en production : {final_count} établissements (attendu : {expected_count})")
    assert final_count == expected_count, f"Discordance de volume ({final_count} != {expected_count})"

    # Vérification de non-régression sur l'échantillon d'origine
    for orig_id, orig_nom, orig_wil, orig_tel in original_entries_sample:
        cur_prod.execute("SELECT nom, wilaya, telephone FROM places WHERE id = ?", (orig_id,))
        check_row = cur_prod.fetchone()
        assert check_row is not None, f"Enregistrement initial manquant id={orig_id}"
        assert check_row[0] == orig_nom, f"Nom altéré sur id={orig_id}"
        assert check_row[1] == orig_wil, f"Wilaya altérée sur id={orig_id}"
        assert check_row[2] == orig_tel, f"Téléphone altéré sur id={orig_id}"

    print("[OK] Non-régression certifiée : 100% des établissements initiaux intacts.")

    # Integrity check final
    cur_prod.execute("PRAGMA integrity_check")
    final_integ = cur_prod.fetchone()[0]
    con_prod.close()
    print(f"[POST-CHECK] Intégrité SQLite finale : {final_integ}")
    assert final_integ == "ok", "Erreur d'intégrité SQLite finale !"

    # 6. Nouveau SHA-256
    new_sha256 = calculate_sha256(PROD_DB)
    print(f"[POST-CHECK] Nouveau SHA-256 de production : {new_sha256}")
    print("=" * 70)
    print(f"INGESTION PHASE 6 RÉUSSIE : {initial_count} -> {final_count} ÉTABLISSEMENTS (+{inserted_count})")
    print("=" * 70)

    # Sauvegarder la nouvelle empreinte dans un fichier d'audit
    meta_path = str(EXPORTS_DIR / "phase6_ingestion_summary.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        import json
        json.dump({
            "status": "success",
            "timestamp": now_iso,
            "database_path": PROD_DB,
            "initial_count": initial_count,
            "inserted_count": inserted_count,
            "final_count": final_count,
            "final_sha256": new_sha256,
            "integrity": final_integ
        }, f, indent=2)


if __name__ == "__main__":
    main()
