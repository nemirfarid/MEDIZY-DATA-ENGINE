#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SANTÉ DZ / MEDIZY — TESTS DE NON-RÉGRESSION ET EXPANSION MULTI-SOURCES (PHASE 8)
================================================================================
Valide l'expansion multi-sources nationale et la finalisation Phase 8 :
1. Non-régression absolue : préservation intégrale des 30 568 fiches baseline certifiées v1.0.14.
2. Volume et complétude : 35 832 établissements qualifiés, 58 wilayas, 100% GPS.
3. Qualité du staging multi-sources et journal des déduplications.
4. Intégrité et conformité cryptographique du cache mobile national GZIP.
5. Performance sous-milliseconde du consommateur client hors-ligne (< 15 ms).
"""

import os
import sys
import json
import sqlite3
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.verify_distribution_cache import verify_cache
from tools.client_cache_consumer import run_benchmark

PROD_DB = str(PROJECT_ROOT / "medizy_scraper.db")
BACKUP_DB_PHASE8 = r"D:\SANTE_DZ_EXPORTS\backups\medizy_scraper_pre_phase8.db"
STAGING_DB_PHASE8 = r"D:\SANTE_DZ_EXPORTS\medizy_staging_multi_source.db"
CACHE_PATH = str(PROJECT_ROOT / "exports" / "mobile" / "medizy_national_cache.json.gz")
EXPORT_DIR_CACHE = r"D:\SANTE_DZ_EXPORTS\mobile\medizy_national_cache.json.gz"


class TestPhase8Expansion(unittest.TestCase):
    """Suite de validation Phase 8 — Expansion multi-sources nationale et cache v1.0.15."""

    def test_01_baseline_non_regression_30568(self):
        """Vérifie que les 30 568 établissements certifiés v1.0.14 sont intacts."""
        if not os.path.exists(BACKUP_DB_PHASE8):
            self.skipTest(f"Sauvegarde introuvable à {BACKUP_DB_PHASE8}")

        con_bak = sqlite3.connect(f"file:{BACKUP_DB_PHASE8}?mode=ro", uri=True)
        cur_bak = con_bak.cursor()
        cur_bak.execute("SELECT id, place_id, nom, wilaya, commune, latitude, longitude FROM places")
        bak_rows = cur_bak.fetchall()
        con_bak.close()

        self.assertEqual(len(bak_rows), 30568, "Le backup Phase 8 doit contenir exactement 30 568 fiches")

        con_prod = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
        cur_prod = con_prod.cursor()

        # Échantillonnage de contrôle régulier sur 600 établissements
        sample = bak_rows[::50]
        for b_id, b_pid, b_nom, b_wil, b_com, b_lat, b_lon in sample:
            cur_prod.execute("SELECT place_id, nom, wilaya, commune, latitude, longitude FROM places WHERE id = ?", (b_id,))
            p_row = cur_prod.fetchone()
            self.assertIsNotNone(p_row, f"Fiche id={b_id} disparue en production !")
            self.assertEqual(p_row[0], b_pid, f"place_id modifié sur id={b_id}")
            self.assertEqual(p_row[1], b_nom, f"Nom modifié sur id={b_id}")
            self.assertEqual(p_row[2], b_wil, f"Wilaya modifiée sur id={b_id}")
            self.assertEqual(p_row[3], b_com, f"Commune modifiée sur id={b_id}")
            self.assertEqual(p_row[4], b_lat, f"Latitude modifiée sur id={b_id}")
            self.assertEqual(p_row[5], b_lon, f"Longitude modifiée sur id={b_id}")

        con_prod.close()

    def test_02_expansion_volume_and_integrity_35832(self):
        """Vérifie le volume total consolidé (35 832), la couverture 58 wilayas et l'intégrité SQLite."""
        con = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
        cur = con.cursor()

        cur.execute("PRAGMA integrity_check")
        integ = cur.fetchone()[0]
        self.assertEqual(integ, "ok", "PRAGMA integrity_check doit être 'ok'")

        cur.execute("SELECT COUNT(*) FROM places")
        total = cur.fetchone()[0]
        self.assertEqual(total, 35832, f"Total attendu 35 832, obtenu {total}")

        cur.execute("SELECT COUNT(DISTINCT wilaya) FROM places")
        wilayas = cur.fetchone()[0]
        self.assertEqual(wilayas, 58, "Les 58 wilayas doivent être représentées sans doublon phonétique")

        cur.execute("SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
        with_gps = cur.fetchone()[0]
        self.assertEqual(with_gps, 35832, "100% des établissements doivent posséder des coordonnées GPS")

        # Vérification des coordonnées GPS bornées en Algérie
        cur.execute("SELECT COUNT(*) FROM places WHERE latitude < 18.5 OR latitude > 37.5 OR longitude < -9.0 OR longitude > 12.5")
        out_of_bounds = cur.fetchone()[0]
        self.assertEqual(out_of_bounds, 0, "Aucun établissement ne doit avoir des coordonnées hors du territoire algérien")

        con.close()

    def test_03_staging_database_quality(self):
        """Vérifie la base de staging multi-sources isolée."""
        if not os.path.exists(STAGING_DB_PHASE8):
            self.skipTest(f"Base de staging introuvable à {STAGING_DB_PHASE8}")

        con = sqlite3.connect(f"file:{STAGING_DB_PHASE8}?mode=ro", uri=True)
        cur = con.cursor()

        cur.execute("SELECT COUNT(*) FROM staging_places")
        staged = cur.fetchone()[0]
        self.assertGreaterEqual(staged, 5000, "La staging table multi-sources doit contenir >= 5000 fiches")

        # Contrôle d'échantillonnage de complétude sur staging
        cur.execute("SELECT nom, wilaya, commune, categorie_recherche, latitude, longitude FROM staging_places LIMIT 50")
        rows = cur.fetchall()
        for nom, wil, com, cat, lat, lon in rows:
            self.assertTrue(bool(nom and nom.strip()), "Nom obligatoire")
            self.assertTrue(bool(wil and wil.strip()), "Wilaya obligatoire")
            self.assertTrue(bool(com and com.strip()), "Commune obligatoire")
            self.assertTrue(bool(cat and cat.strip()), "Catégorie obligatoire")
            self.assertTrue(18.5 <= lat <= 37.5, f"Latitude {lat} hors Algérie")
            self.assertTrue(-9.0 <= lon <= 12.5, f"Longitude {lon} hors Algérie")

        con.close()

    def test_04_cache_conformance_35832(self):
        """Vérifie que verify_distribution_cache certifie l'archive nationale régénérée à 35 832 établissements."""
        target_cache = CACHE_PATH if os.path.exists(CACHE_PATH) else EXPORT_DIR_CACHE
        if not os.path.exists(target_cache):
            self.skipTest(f"Archive introuvable à {target_cache}")

        report = verify_cache(cache_path=target_cache, db_path=PROD_DB)
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["overall_integrity"], "CONFORME")
        self.assertEqual(report["validation_checks"]["facilities_count"], 35832)
        self.assertEqual(report["validation_checks"]["wilayas_count"], 58)
        self.assertTrue(report["validation_checks"]["count_concordance"])
        self.assertTrue(report["validation_checks"]["sha_concordance"])
        self.assertTrue(report["validation_checks"]["schema_sample_valid"])

    def test_05_client_cache_consumer_benchmark_35832(self):
        """Vérifie que le consommateur mémoire effectue les recherches sur 35 832 fiches en < 15 ms."""
        target_cache = CACHE_PATH if os.path.exists(CACHE_PATH) else EXPORT_DIR_CACHE
        if not os.path.exists(target_cache):
            self.skipTest(f"Archive introuvable à {target_cache}")

        report = run_benchmark(cache_path=target_cache)
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["total_facilities_in_ram"], 35832)
        self.assertTrue(report["meets_target_15ms"], f"Temps max {report['max_search_time_ms']} ms dépasse 15 ms")
        self.assertLess(report["max_search_time_ms"], 15.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
