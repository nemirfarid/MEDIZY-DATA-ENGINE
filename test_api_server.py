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

import gzip
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
        self.assertEqual(data["database"]["total_entries"], 30568)
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

    def test_08_openapi_spec(self):
        """Valide la spécification OpenAPI 3.0 sur /openapi.json."""
        status, data = self._get("/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(data["openapi"], "3.0.3")
        self.assertIn("info", data)
        self.assertEqual(data["info"]["version"], "1.0.9")
        self.assertIn("/api/v1/search", data["paths"])
        self.assertIn("/api/v1/nearby", data["paths"])
        self.assertIn("Facility", data["components"]["schemas"])

    def test_09_swagger_docs(self):
        """Valide la page Swagger UI sur /docs."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/docs"
        req = urllib.request.Request(url, headers={"User-Agent": "MedizyTestClient/1.0"})
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            self.assertEqual(resp.status, 200)
            self.assertIn("SwaggerUIBundle", content)
            self.assertIn("/openapi.json", content)

    def test_10_cache_version(self):
        """Valide la route /api/v1/cache/version pour la synchronisation client."""
        status, data = self._get("/api/v1/cache/version")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_facilities"], 30568)
        self.assertEqual(data["total_wilayas"], 58)
        self.assertEqual(data["database_sha256"], MedizyAPIHandler.db_sha256)
        self.assertIn("national_cache", data)
        self.assertEqual(data["national_cache"]["download_url"], "/api/v1/cache/national")

    def test_11_cache_national_download(self):
        """Valide le téléchargement et la décompression de l'archive nationale complète."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/api/v1/cache/national"
        req = urllib.request.Request(url, headers={"User-Agent": "MedizyTestClient/1.0"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("application/gzip", resp.headers.get("Content-Type", ""))
            self.assertIn("medizy_national_cache.json.gz", resp.headers.get("Content-Disposition", ""))
            raw_bytes = resp.read()
            # Vérification du nombre magique GZIP (0x1f, 0x8b)
            self.assertEqual(raw_bytes[:2], b"\x1f\x8b")
            
            # Décompression et validation JSON
            decompressed = gzip.decompress(raw_bytes).decode("utf-8")
            parsed = json.loads(decompressed)
            self.assertEqual(parsed["metadata"]["package_type"], "national_consolidated")
            self.assertEqual(len(parsed["facilities"]), 30568)

    def test_12_cache_wilaya_download(self):
        """Valide le téléchargement du cache partitionné par wilaya (ex: 16 Alger)."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/api/v1/cache/wilaya/16"
        req = urllib.request.Request(url, headers={"User-Agent": "MedizyTestClient/1.0"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("application/gzip", resp.headers.get("Content-Type", ""))
            raw_bytes = resp.read()
            self.assertEqual(raw_bytes[:2], b"\x1f\x8b")

            decompressed = gzip.decompress(raw_bytes).decode("utf-8")
            parsed = json.loads(decompressed)
            self.assertEqual(parsed["metadata"]["wilaya"], "Alger")
            self.assertEqual(parsed["metadata"]["wilaya_code"], "16")
            self.assertGreater(len(parsed["facilities"]), 0)

    def test_13_cache_invalid_wilaya(self):
        """Valide le rejet d'une wilaya inexistante sur le cache."""
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/v1/cache/wilaya/999")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
