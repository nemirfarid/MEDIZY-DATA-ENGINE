#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module d'export de cache mobile (Phase 10)
==================================================================
Valide :
- Export par wilaya
- Compression GZIP et intégrité de relecture
- Présence des métadonnées requises
"""

import gzip
import json
import os
import shutil
import tempfile
import unittest

from export_mobile_cache import export_wilaya, export_records_to_gzip, DB_PATH


class TestExportMobileCache(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_export_wilaya_oran(self):
        """Valide l'export de la wilaya d'Oran (code 31)."""
        stat = export_wilaya("31", output_dir=self.test_dir)
        self.assertTrue(os.path.exists(stat["filepath"]))
        self.assertGreater(stat["records_count"], 0)
        self.assertGreater(stat["compression_ratio_pct"], 50.0)

        # Vérification du contenu JSON décompressé
        with gzip.open(stat["filepath"], "rt", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["metadata"]["wilaya"], "Oran")
            self.assertEqual(data["metadata"]["wilaya_code"], "31")
            self.assertEqual(len(data["facilities"]), stat["records_count"])
            # Vérification de la structure d'une fiche
            first = data["facilities"][0]
            self.assertIn("nom", first)
            self.assertIn("lat", first)
            self.assertIn("lon", first)
            self.assertIn("cat", first)

    def test_02_invalid_wilaya(self):
        """Vérifie le rejet d'une wilaya inexistante."""
        with self.assertRaises(ValueError):
            export_wilaya("Wilaya999Inexistante", output_dir=self.test_dir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
