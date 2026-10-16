#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests d'intégration HTTP pour le serveur API REST (Phase 9)
===========================================================
Valide :
- GET /health
- GET /api/v1/search
- GET /api/v1/nearby
- GET /api/v1/places/<id>
- GET /api/v1/wilayas
- GET /api/v1/categories
"""

import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from api_server import MedizyAPIHandler, calculate_sha256, DB_PATH
from medizy_search import MedizySearchEngine

TEST_HOST = "127.0.0.1"
TEST_PORT = 8899


class TestMedizyAPIServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Lance le serveur HTTP dans un thread séparé pour les tests."""
        cls.engine = MedizySearchEngine(db_path=DB_PATH)
        MedizyAPIHandler.engine = cls.engine
        MedizyAPIHandler.db_sha256 = calculate_sha256(DB_PATH)

        cls.httpd = ThreadingHTTPServer((TEST_HOST, TEST_PORT), MedizyAPIHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        """Arrête le serveur HTTP."""
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.engine.close()

    def _get(self, path: str):
        url = f"http://{TEST_HOST}:{TEST_PORT}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "MedizyTestClient/1.0"})
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            return resp.status, json.loads(data)

    def test_01_health_endpoint(self):
        """Valide la route /health."""
        status, data = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"]["total_entries"], 23669)
        self.assertEqual(data["database"]["sqlite_integrity"], "ok")
        self.assertEqual(data["database"]["mode"], "read_only")
        self.assertEqual(data["coverage"]["wilayas_covered"], 58)

    def test_02_search_endpoint(self):
        """Valide la route /api/v1/search avec filtres multicritères."""
        status, data = self._get("/api/v1/search?wilaya=16&specialite=cardio&limit=5")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["total_count"], 0)
        self.assertLessEqual(len(data["data"]), 5)
        for item in data["data"]:
            self.assertEqual(item["wilaya"], "Alger")

    def test_03_nearby_endpoint(self):
        """Valide la route /api/v1/nearby (recherche géospatiale 5 km)."""
        status, data = self._get("/api/v1/nearby?lat=36.7538&lon=3.0588&radius_km=5.0&limit=5")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["total_count"], 0)
        self.assertLessEqual(len(data["data"]), 5)
        
        # Vérification du tri ascendant des distances
        prev_dist = 0.0
        for item in data["data"]:
            dist = item["distance_km"]
            self.assertIsNotNone(dist)
            self.assertLessEqual(dist, 5.0)
            self.assertGreaterEqual(dist, prev_dist)
            prev_dist = dist

    def test_04_wilayas_endpoint(self):
        """Valide la route /api/v1/wilayas."""
        status, data = self._get("/api/v1/wilayas")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["wilayas_count"], 58)
        self.assertEqual(len(data["data"]), 58)

    def test_05_categories_endpoint(self):
        """Valide la route /api/v1/categories."""
        status, data = self._get("/api/v1/categories")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["categories_count"], 0)

    def test_06_places_by_id(self):
        """Valide la route /api/v1/places/<id>."""
        # Récupération d'un ID valide depuis search
        _, search_data = self._get("/api/v1/search?limit=1")
        test_id = search_data["data"][0]["id"]

        status, data = self._get(f"/api/v1/places/{test_id}")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["id"], test_id)
        self.assertIsNotNone(data["data"]["nom"])

    def test_07_error_handling(self):
        """Valide la gestion des erreurs (404 et 400)."""
        # Route inexistante -> 404
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/v1/route_inconnue")
        self.assertEqual(ctx.exception.code, 404)

        # Nearby sans paramètres lat/lon -> 400
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/v1/nearby")
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
