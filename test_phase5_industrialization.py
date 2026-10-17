#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Tests d'Industrialisation Phase 5
=====================================================
Validation complète :
1. Conformité cryptographique et structurelle de l'archive GZIP (verify_distribution_cache).
2. Performances et exactitude du consommateur mémoire client (< 15 ms).
3. Disponibilité du serveur API et validation du endpoint /stats.
4. Négociation de contenu GZIP et headers CORS.
"""

import gzip
import json
import os
import sys
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from api_server import MedizyAPIHandler, calculate_sha256, DB_PATH
from medizy_search import MedizySearchEngine
from tools.verify_distribution_cache import verify_cache
from tools.client_cache_consumer import run_benchmark, MemoryCacheSearcher

TEST_HOST = "127.0.0.1"
TEST_PORT = 8898


class TestPhase5Industrialization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialise un serveur API de test en tâche de fond."""
        cls.engine = MedizySearchEngine(db_path=DB_PATH)
        MedizyAPIHandler.engine = cls.engine
        MedizyAPIHandler.db_sha256 = calculate_sha256(DB_PATH)

        cls.httpd = ThreadingHTTPServer((TEST_HOST, TEST_PORT), MedizyAPIHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        """Arrête le serveur HTTP de test."""
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.engine.close()

    def _get(self, path: str, headers=None):
        url = f"http://{TEST_HOST}:{TEST_PORT}{path}"
        req_headers = {"User-Agent": "MedizyIndustrializationTest/1.0"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req) as resp:
            content_encoding = resp.headers.get("Content-Encoding")
            cors_header = resp.headers.get("Access-Control-Allow-Origin")
            raw_body = resp.read()
            if content_encoding == "gzip":
                decompressed = gzip.decompress(raw_body).decode("utf-8")
                return resp.status, json.loads(decompressed), resp.headers
            else:
                return resp.status, json.loads(raw_body.decode("utf-8")), resp.headers

    def test_01_verify_distribution_cache_conformance(self):
        """Vérifie que verify_distribution_cache certifie l'archive nationale."""
        report = verify_cache()
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["overall_integrity"], "CONFORME")
        self.assertEqual(report["validation_checks"]["facilities_count"], 23669)
        self.assertEqual(report["validation_checks"]["wilayas_count"], 58)
        self.assertTrue(report["validation_checks"]["count_concordance"])
        self.assertTrue(report["validation_checks"]["sha_concordance"])
        self.assertTrue(report["validation_checks"]["schema_sample_valid"])

    def test_02_memory_cache_consumer_performance(self):
        """Vérifie que le consommateur mémoire effectue les requêtes types en < 15 ms."""
        report = run_benchmark()
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["total_facilities_in_ram"], 23669)
        self.assertTrue(report["meets_target_15ms"], f"Temps max {report['max_search_time_ms']} ms dépasse 15 ms")
        self.assertLess(report["max_search_time_ms"], 15.0)

        # Vérification des résultats de la requête 1 : "cardiologue" à Oran
        b1 = report["benchmarks"][0]["metrics"]
        self.assertEqual(b1["total_matches"], 10)
        self.assertLess(b1["elapsed_ms"], 15.0)
        for f in b1["results"]:
            self.assertEqual(f["wil"], "Oran")
            self.assertIn("cardio", f["cat"].lower())

    def test_03_api_server_stats_endpoint(self):
        """Vérifie le endpoint /api/v1/stats et la concordance des métriques en direct."""
        status, data, headers = self._get("/api/v1/stats")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        metrics = data["metrics"]
        self.assertEqual(metrics["total_facilities"], 23669)
        self.assertEqual(metrics["wilayas_covered"], 58)
        self.assertGreater(metrics["with_phone"], 15000)
        self.assertEqual(metrics["with_gps"], 23669)
        self.assertEqual(metrics["gps_coverage_pct"], 100.0)
        self.assertEqual(metrics["database_sha256"], "69b94b3ca03d80d5ea33f8395482c6763e72d1fba5c491300b0e92dcd6d12e65")

        # Vérification des sources
        sources = metrics["sources_breakdown"]
        self.assertIn("Google Maps public UI", sources)
        self.assertGreater(sources["Google Maps public UI"], 23000)

    def test_04_cors_and_gzip_compression(self):
        """Vérifie les headers CORS et la compression dynamique GZIP des réponses."""
        status, data, headers = self._get("/api/v1/health", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(headers.get("Content-Encoding"), "gzip")
        self.assertEqual(data["status"], "healthy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
