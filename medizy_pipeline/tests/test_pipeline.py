#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Suite de Tests Unitaires et d'Intégration
============================================================
Validation du classificateur, du moteur de déduplication spatiale,
du parseur d'URL Google Maps et de la logique de recherche avec badges.
"""

import math
import os
import sys
import unittest

# Assurer l'accès au package medizy_pipeline
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from medizy_pipeline.enrichment.classifier import (
    classify_facility,
    normalize_algerian_phone,
    normalize_text,
)
from medizy_pipeline.enrichment.deduplication import (
    compute_name_similarity,
    haversine_distance_meters,
    is_duplicate_match,
)
from medizy_pipeline.enrichment.url_parser import extract_coordinates_from_url
from medizy_pipeline.api.db import DatabaseService, build_badge
from medizy_pipeline.api.schemas import FacilitySearchQuery, FacilityType


class TestClassifier(unittest.TestCase):
    def test_algerian_health_classification(self):
        cases = [
            ("CHU Mustapha Pacha Alger", "CHU"),
            ("Centre Hospitalo-Universitaire Neddir Mohamed", "CHU"),
            ("EPH Rouiba Hôpital", "EPH"),
            ("Établissement Public Hospitalier de Boufarik", "EPH"),
            ("EPSP Bab El Oued", "EPSP"),
            ("EHS Maternité Sainte Thérèse", "EHS"),
            ("Polyclinique Larbi Tebessi", "Polyclinique"),
            ("Poly-clinique des Martyrs", "Polyclinique"),
            ("Clinique Médico-Chirurgicale Al Azhar", "Clinique"),
            ("Clinique Ophtalmologique Diar Es Saada", "Clinique"),
            ("Pavillon des Urgences Médico-Chirurgicales UMC", "Urgences"),
            ("Salle de soins Oued Smar", "Dispensaire"),
            ("Centre de santé de proximité", "Centre de Santé"),
            ("Cabinet Médical Dr. Benali Mohamed", "Cabinet Médical"),
            ("Hôpital Militaire Régional Universitaire", "Hôpital"),
        ]
        for name, expected_type in cases:
            detected = classify_facility(name)
            self.assertEqual(detected, expected_type, f"Échec pour '{name}': obtenu '{detected}' au lieu de '{expected_type}'")

    def test_phone_normalization(self):
        cases = [
            ("021 23 45 67", "+21321234567"),
            ("00213 23 45 67 89", "+21323456789"),
            ("213550123456", "+213550123456"),
            ("0550 12 34 56", "+213550123456"),
        ]
        for raw, expected_e164 in cases:
            e164, disp = normalize_algerian_phone(raw)
            self.assertEqual(e164, expected_e164)
            self.assertTrue(disp.startswith("+213"))


class TestDeduplication(unittest.TestCase):
    def test_haversine_distance(self):
        # Coordonnées proches à Alger : Grande Poste (36.7753, 3.0588) et Place Maurice Audin (36.7725, 3.0560) ~ 400m
        d = haversine_distance_meters(36.7753, 3.0588, 36.7725, 3.0560)
        self.assertTrue(350 <= d <= 450, f"Distance calculée inattendue: {d}m")

        # Même point
        d_zero = haversine_distance_meters(36.75, 3.05, 36.75, 3.05)
        self.assertAlmostEqual(d_zero, 0.0, places=3)

    def test_name_similarity(self):
        # Variantes d'une même clinique
        sim1 = compute_name_similarity("Clinique Al Azhar", "Clinique Medico-Chirurgicale Al Azhar")
        self.assertGreaterEqual(sim1, 0.70)

        # Hôpitaux complètement différents
        sim2 = compute_name_similarity("CHU Mustapha Alger", "EPH Rouiba")
        self.assertLess(sim2, 0.40)

    def test_duplicate_matching_rules(self):
        existing = {
            "name": "Polyclinique Sidi M'Hamed",
            "latitude": 36.7550,
            "longitude": 3.0520,
            "google_place_id": "ChIJ12345",
            "osm_id": "node/999",
        }

        # Cas 1 : Exactement le même place_id
        matched, dist, sim, reason = is_duplicate_match(
            cand_lat=36.7550, cand_lon=3.0520, cand_name="Autre nom",
            cand_google_id="ChIJ12345", cand_osm_id=None,
            existing_facility=existing
        )
        self.assertTrue(matched)
        self.assertEqual(reason, "EXACT_GOOGLE_PLACE_ID")

        # Cas 2 : À 35 mètres de distance avec nom équivalent
        matched, dist, sim, reason = is_duplicate_match(
            cand_lat=36.7552, cand_lon=3.0522, cand_name="Poly-clinique Sidi Mohamed",
            cand_google_id=None, cand_osm_id=None,
            existing_facility=existing, max_distance_meters=100.0
        )
        self.assertTrue(matched)
        self.assertLessEqual(dist, 100.0)

        # Cas 3 : À 350 mètres de distance (hors rayon de 100m)
        matched, dist, sim, reason = is_duplicate_match(
            cand_lat=36.7580, cand_lon=3.0550, cand_name="Polyclinique Sidi M'Hamed",
            cand_google_id=None, cand_osm_id=None,
            existing_facility=existing, max_distance_meters=100.0
        )
        self.assertFalse(matched)
        self.assertGreater(dist, 100.0)


class TestGoogleMapsExtractor(unittest.TestCase):
    def test_url_extraction(self):
        urls = [
            ("https://maps.google.com/?q=36.752887,3.058823", 36.752887, 3.058823),
            ("https://www.google.com/maps/place/CHU/@36.768212,3.031544,17z/data=...", 36.768212, 3.031544),
            ("https://www.google.com/maps?ll=35.698711,-0.634922&z=15", 35.698711, -0.634922),
            ("https://maps.google.com/maps?q=loc:36.7123,3.1890", 36.7123, 3.1890),
        ]
        for url, exp_lat, exp_lon in urls:
            lat, lon = extract_coordinates_from_url(url)
            self.assertIsNotNone(lat, f"Échec extraction pour {url}")
            self.assertIsNotNone(lon, f"Échec extraction pour {url}")
            self.assertAlmostEqual(lat, exp_lat, places=4)
            self.assertAlmostEqual(lon, exp_lon, places=4)


class TestDatabaseAndBadges(unittest.TestCase):
    def setUp(self):
        # Utiliser une base SQLite de test dédiée
        self.test_db_path = "medizy_test_facilities.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        os.environ["SQLITE_DB_PATH"] = self.test_db_path
        self.db = DatabaseService()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except:
                pass

    def test_badges_generation(self):
        # Non revendiqué (public)
        unclaimed_badge = build_badge(is_claimed=False, is_verified=False, facility_id=42)
        self.assertEqual(unclaimed_badge.label, "Fiche informative publique")
        self.assertEqual(unclaimed_badge.variant, "info")
        self.assertTrue(unclaimed_badge.can_claim)
        self.assertEqual(unclaimed_badge.claim_url, "/facilities/42/claim")

        # Revendiqué
        claimed_badge = build_badge(is_claimed=True, is_verified=True, facility_id=42)
        self.assertEqual(claimed_badge.label, "Établissement revendiqué et vérifié")
        self.assertEqual(claimed_badge.variant, "success")
        self.assertFalse(claimed_badge.can_claim)
        self.assertIsNone(claimed_badge.claim_url)

    def test_search_and_unclaimed_inclusion(self):
        # Insertion manuelle de deux structures dans SQLite
        conn = self.db._get_sqlite_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS facilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                wilaya TEXT NOT NULL,
                wilaya_code TEXT,
                commune TEXT,
                address TEXT,
                phone TEXT,
                phone_normalized TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                is_claimed INTEGER DEFAULT 0,
                is_verified INTEGER DEFAULT 0,
                source TEXT DEFAULT 'manual',
                google_place_id TEXT UNIQUE,
                osm_id TEXT UNIQUE,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # 1. Structure non revendiquée (publique issue d'OSM)
        cur.execute("""
            INSERT INTO facilities (name, type, wilaya, wilaya_code, latitude, longitude, is_claimed, source)
            VALUES ('Polyclinique Publique Test', 'Polyclinique', 'Alger', '16', 36.7500, 3.0500, 0, 'openstreetmap')
        """)
        # 2. Structure revendiquée privée
        cur.execute("""
            INSERT INTO facilities (name, type, wilaya, wilaya_code, latitude, longitude, is_claimed, source)
            VALUES ('Clinique Privée Test', 'Clinique', 'Alger', '16', 36.7510, 3.0510, 1, 'manual')
        """)
        conn.commit()
        conn.close()

        # Requête de recherche sans filtre is_claimed : Doit retourner les 2 établissements !
        q = FacilitySearchQuery(
            lat=36.7500,
            lon=3.0500,
            radius_km=5.0,
            wilaya="Alger",
        )
        total, results = self.db.search_facilities(q)
        self.assertEqual(total, 2)
        self.assertEqual(len(results), 2)

        # Vérifier la présence et le badge de la fiche publique
        public_fac = next((f for f in results if not f.is_claimed), None)
        self.assertIsNotNone(public_fac)
        self.assertEqual(public_fac.badge.label, "Fiche informative publique")
        self.assertEqual(public_fac.badge.variant, "info")

        # Vérifier la présence et le badge de la fiche revendiquée
        claimed_fac = next((f for f in results if f.is_claimed), None)
        self.assertIsNotNone(claimed_fac)
        self.assertEqual(claimed_fac.badge.label, "Établissement revendiqué et vérifié")
        self.assertEqual(claimed_fac.badge.variant, "success")


class TestFastAPIEndpoints(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from medizy_pipeline.api.main import app

        self.test_db_path = "medizy_api_test.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        os.environ["SQLITE_DB_PATH"] = self.test_db_path

        # Pré-remplir avec une structure
        db = DatabaseService()
        conn = db._get_sqlite_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS facilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                wilaya TEXT NOT NULL,
                wilaya_code TEXT,
                commune TEXT,
                address TEXT,
                phone TEXT,
                phone_normalized TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                is_claimed INTEGER DEFAULT 0,
                is_verified INTEGER DEFAULT 0,
                source TEXT DEFAULT 'manual',
                google_place_id TEXT UNIQUE,
                osm_id TEXT UNIQUE,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cur.execute("""
            INSERT INTO facilities (name, type, wilaya, wilaya_code, commune, latitude, longitude, is_claimed, is_verified, source)
            VALUES ('EPH Bologhine Ibn Ziri', 'EPH', 'Alger', '16', 'Bologhine', 36.7900, 3.0450, 0, 0, 'openstreetmap')
        """)
        conn.commit()
        conn.close()

        self.client = TestClient(app)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except:
                pass

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")

    def test_search_endpoint_with_unclaimed_badge(self):
        resp = self.client.get("/api/v1/facilities/search?wilaya=Alger&radius_km=15")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["total"], 1)
        facility = data["data"][0]
        self.assertEqual(facility["name"], "EPH Bologhine Ibn Ziri")
        self.assertEqual(facility["badge"]["label"], "Fiche informative publique")
        self.assertEqual(facility["badge"]["variant"], "info")
        self.assertTrue(facility["badge"]["can_claim"])

    def test_community_suggestion_with_google_maps_url(self):
        payload = {
            "name": "Polyclinique El Biar Nouvelle",
            "type": "Polyclinique",
            "wilaya": "Alger",
            "commune": "El Biar",
            "google_maps_url": "https://maps.google.com/?q=36.768212,3.031544",
            "phone": "021 92 11 22",
            "submitter_name": "Dr. Mourad",
            "submitter_notes": "Structure publique ouverte jour et nuit avec service de garde.",
        }
        resp = self.client.post("/api/v1/facilities/suggest", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["status"], "PENDING")
        self.assertIsNotNone(data["suggestion_id"])
        self.assertIsNotNone(data["parsed_coordinates"])
        self.assertAlmostEqual(data["parsed_coordinates"]["latitude"], 36.768212, places=4)
        self.assertAlmostEqual(data["parsed_coordinates"]["longitude"], 3.031544, places=4)

    def test_admin_moderation_workflow(self):
        # 1. Tester le rejet si pas d'authentification
        unauth_resp = self.client.get("/api/v1/admin/suggestions")
        self.assertEqual(unauth_resp.status_code, 401)

        # 2. Authentification JWT via POST /api/v1/admin/auth/login
        bad_login = self.client.post("/api/v1/admin/auth/login", json={
            "username": "admin@medizy.dz",
            "password": "WrongPassword123"
        })
        self.assertEqual(bad_login.status_code, 401)

        good_login = self.client.post("/api/v1/admin/auth/login", json={
            "username": "admin@medizy.dz",
            "password": "MedizyAdmin2026!"
        })
        self.assertEqual(good_login.status_code, 200)
        token_data = good_login.json()
        self.assertIn("access_token", token_data)
        jwt_token = token_data["access_token"]
        jwt_headers = {"Authorization": f"Bearer {jwt_token}"}

        # 3. Soumettre deux suggestions
        sugg1_resp = self.client.post("/api/v1/facilities/suggest", json={
            "name": "Clinique Al Azhar Test",
            "type": "Clinique",
            "wilaya": "Alger",
            "google_maps_url": "https://maps.google.com/?q=36.7512,3.0321",
        })
        sugg1_id = sugg1_resp.json()["suggestion_id"]

        sugg2_resp = self.client.post("/api/v1/facilities/suggest", json={
            "name": "Faux Dispensaire Fermé",
            "type": "Dispensaire",
            "wilaya": "Oran",
            "google_maps_url": "https://maps.google.com/?q=35.6987,-0.6349",
        })
        sugg2_id = sugg2_resp.json()["suggestion_id"]

        # 4. Lister les suggestions PENDING avec jeton JWT
        list_resp = self.client.get("/api/v1/admin/suggestions?status=PENDING", headers=jwt_headers)
        self.assertEqual(list_resp.status_code, 200)
        self.assertIn("x-ratelimit-limit", list_resp.headers)
        list_data = list_resp.json()
        self.assertGreaterEqual(list_data["total"], 2)

        # 5. Approuver sugg1 avec jeton JWT
        appr_resp = self.client.post(
            f"/api/v1/admin/suggestions/{sugg1_id}/approve",
            headers=jwt_headers,
            json={
                "moderator_name": "Dr. Benali (DSP Alger)",
                "moderation_comment": "Établissement vérifié et opérationnel.",
            },
        )
        self.assertEqual(appr_resp.status_code, 200)
        appr_data = appr_resp.json()
        self.assertEqual(appr_data["status"], "APPROVED")
        created_fac = appr_data["facility"]
        self.assertEqual(created_fac["name"], "Clinique Al Azhar Test")
        self.assertEqual(created_fac["source"], "community_suggestion")
        self.assertTrue(created_fac["is_verified"])

        # 6. Rejeter sugg2 avec jeton JWT
        rej_resp = self.client.post(
            f"/api/v1/admin/suggestions/{sugg2_id}/reject",
            headers=jwt_headers,
            json={
                "reason": "Établissement fermé définitivement.",
                "moderator_name": "Dr. Benali (DSP Alger)",
            },
        )
        self.assertEqual(rej_resp.status_code, 200)
        self.assertEqual(rej_resp.json()["status"], "REJECTED")

        # 7. Tester également la compatibilité de secours avec clé API système
        fallback_resp = self.client.get(
            "/api/v1/admin/suggestions?status=PENDING",
            headers={"X-Admin-Api-Key": "medizy-admin-secret-key-2026"}
        )
        self.assertEqual(fallback_resp.status_code, 200)

    def test_prometheus_metrics_endpoint(self):
        """Vérifie l'exposition et le format des métriques Prometheus."""
        resp = self.client.get("/metrics")
        self.assertEqual(resp.status_code, 200)
        metrics_text = resp.text
        self.assertIn("pending_suggestions_gauge", metrics_text)
        self.assertIn("osm_mirror_failover_total", metrics_text)
        self.assertIn("medizy_geosearch_duration_seconds", metrics_text)
        self.assertIn("medizy_backup_success_status", metrics_text)
        self.assertIn("medizy_last_backup_timestamp", metrics_text)

    def test_nibras_export_latest_endpoint(self):
        """Vérifie la passerelle de synchronisation externe pour NIBRAS."""
        resp = self.client.get("/api/v1/facilities/export/latest?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("facilities", data)
        self.assertIn("sync_timestamp", data)
        self.assertGreaterEqual(data["count"], 1)

        fac = data["facilities"][0]
        self.assertEqual(fac["name"], "EPH Bologhine Ibn Ziri")
        self.assertIn("embedding_context", fac)
        self.assertIn("Wilaya de Alger", fac["embedding_context"])

    def test_read_only_mode_middleware(self):
        """Vérifie l'interception des requêtes mutantes en mode lecture seule."""
        # 1. Mode normal (read_write)
        os.environ["READ_ONLY_MODE"] = "false"
        health_resp = self.client.get("/health")
        self.assertEqual(health_resp.status_code, 200)
        self.assertEqual(health_resp.json()["mode"], "read_write")

        # 2. Activation du mode lecture seule
        os.environ["READ_ONLY_MODE"] = "true"
        try:
            health_ro = self.client.get("/health")
            self.assertEqual(health_ro.status_code, 200)
            self.assertEqual(health_ro.json()["mode"], "read_only")

            # Les requêtes en lecture restent 100% fonctionnelles
            read_resp = self.client.get("/api/v1/facilities/nearby?lat=36.75&lon=3.05")
            self.assertEqual(read_resp.status_code, 200)

            # Les requêtes en écriture sont bloquées avec HTTP 503
            write_resp = self.client.post(
                "/api/v1/facilities/suggest",
                json={
                    "name": "Cabinet Test Mode RO",
                    "wilaya": "Alger",
                    "latitude": 36.75,
                    "longitude": 3.05,
                },
            )
            self.assertEqual(write_resp.status_code, 503)
            self.assertEqual(write_resp.json()["error"], "READ_ONLY_MODE")
        finally:
            # Rétablissement du mode nominal
            os.environ["READ_ONLY_MODE"] = "false"


if __name__ == "__main__":
    unittest.main()



