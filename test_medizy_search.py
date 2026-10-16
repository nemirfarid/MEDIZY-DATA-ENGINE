#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le moteur de recherche Medizy (Phase 9)
=============================================================
Validation de :
1. Recherche par rayon géographique (Haversine + Bounding Box).
2. Recherche multicritère (wilaya, commune, spécialité, texte libre).
3. Conformité des temps de réponse (< 50 ms en recherche indexée).
4. Protection absolue en lecture seule de medizy_scraper.db.
"""

import os
import sqlite3
import time
import unittest
from medizy_search import MedizySearchEngine, haversine_distance

DB_PATH = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"


class TestMedizySearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialisation du moteur de recherche pour la suite de tests."""
        cls.engine = MedizySearchEngine(db_path=DB_PATH)
        # Préchauffage du cache SQLite
        cls.engine.search(wilaya="Alger", limit=1)

    def test_01_read_only_protection(self):
        """Vérifie que la base est strictement protégée en lecture seule."""
        conn = self.engine._get_connection()
        cur = conn.cursor()
        with self.assertRaises(sqlite3.OperationalError):
            cur.execute("INSERT INTO places (nom) VALUES ('Test Interdit');")
        with self.assertRaises(sqlite3.OperationalError):
            cur.execute("UPDATE places SET nom = 'Hack' WHERE id = 1;")
        conn.close()

    def test_02_wilaya_resolution(self):
        """Vérifie la normalisation des codes et noms de wilayas."""
        self.assertEqual(self.engine.resolve_wilaya("16"), "Alger")
        self.assertEqual(self.engine.resolve_wilaya("31"), "Oran")
        self.assertEqual(self.engine.resolve_wilaya("07"), "Biskra")
        self.assertEqual(self.engine.resolve_wilaya("alger"), "Alger")
        self.assertEqual(self.engine.resolve_wilaya("oran"), "Oran")
        self.assertEqual(self.engine.resolve_wilaya("setif"), "Sétif")
        self.assertEqual(self.engine.resolve_wilaya("tizi ouzou"), "Tizi Ouzou")

    def test_03_nearby_search_alger_centre(self):
        """Vérifie la recherche géospatiale par rayon de 5 km autour d'Alger Centre."""
        lat_alger = 36.7538
        lon_alger = 3.0588
        radius_km = 5.0

        res = self.engine.search(latitude=lat_alger, longitude=lon_alger, radius_km=radius_km, limit=20)

        self.assertGreater(res.total_count, 0, "Doit trouver des établissements à Alger Centre")
        self.assertLessEqual(len(res.results), 20)

        # Vérification des distances
        previous_distance = 0.0
        for item in res.results:
            dist = item.get("distance_km")
            self.assertIsNotNone(dist, "La distance doit être calculée")
            self.assertLessEqual(dist, radius_km, f"Distance {dist} doit être <= {radius_km} km")
            self.assertGreaterEqual(dist, previous_distance, "Les résultats doivent être triés par distance croissante")
            previous_distance = dist
            self.assertIsNotNone(item.get("nom"))
            self.assertIsNotNone(item.get("latitude"))
            self.assertIsNotNone(item.get("longitude"))

    def test_04_nearby_with_specialty_filter(self):
        """Vérifie la combinaison rayon GPS + spécialité médicale (ex: pharmacie)."""
        lat_oran = 35.6976
        lon_oran = -0.6337
        radius_km = 8.0

        res = self.engine.search(
            latitude=lat_oran,
            longitude=lon_oran,
            radius_km=radius_km,
            specialite="pharmacie",
            limit=15
        )

        self.assertGreater(res.total_count, 0, "Doit trouver des pharmacies à Oran")
        for item in res.results:
            self.assertLessEqual(item["distance_km"], radius_km)
            self.assertIn("pharmacie", item["categorie_recherche"].lower())

    def test_05_multicriteria_search(self):
        """Vérifie la recherche multicritère (wilaya + spécialité + texte libre)."""
        res = self.engine.search(
            wilaya="Alger",
            specialite="dentiste",
            query="cabinet",
            limit=10
        )

        self.assertGreater(res.total_count, 0, "Doit retourner des résultats")
        for item in res.results:
            self.assertEqual(item["wilaya"], "Alger")
            self.assertTrue(
                "dent" in item["categorie_recherche"].lower() or "dentiste" in item["nom"].lower(),
                "Doit correspondre à la spécialité dentaire"
            )

    def test_06_commune_filter(self):
        """Vérifie le filtrage par commune au sein d'une wilaya."""
        res = self.engine.search(wilaya="Alger", commune="Kouba", limit=10)
        self.assertGreater(res.total_count, 0, "Doit trouver des établissements à Kouba")
        for item in res.results:
            self.assertEqual(item["wilaya"], "Alger")
            self.assertIn("kouba", item["commune"].lower())

    def test_07_full_text_keyword_search(self):
        """Vérifie la recherche libre multi-champs avec tolérance."""
        res = self.engine.search(query="Pasteur", limit=5)
        self.assertGreater(res.total_count, 0, "Doit trouver des établissements nommés Pasteur")
        found_pasteur = any("pasteur" in r["nom"].lower() for r in res.results)
        self.assertTrue(found_pasteur)

    def test_08_pagination(self):
        """Vérifie la conformité de la pagination."""
        page1 = self.engine.search(wilaya="Constantine", limit=5, offset=0)
        page2 = self.engine.search(wilaya="Constantine", limit=5, offset=5)

        self.assertEqual(len(page1.results), 5)
        self.assertEqual(len(page2.results), 5)
        self.assertEqual(page1.page, 1)
        self.assertEqual(page2.page, 2)
        # Les IDs ne doivent pas se chevaucher
        ids_p1 = {r["id"] for r in page1.results}
        ids_p2 = {r["id"] for r in page2.results}
        self.assertEqual(len(ids_p1.intersection(ids_p2)), 0)

    def test_09_performance_response_times(self):
        """Vérifie que les temps de réponse sur requêtes indexées respectent le seuil (< 50 ms)."""
        # Test 1 : Requête par Wilaya (indexée sur idx_places_wilaya)
        _ = self.engine.search(wilaya="Oran", limit=1)
        res_wil = self.engine.search(wilaya="Oran", limit=20)
        self.assertLess(
            res_wil.execution_time_ms,
            50.0,
            f"Recherche par wilaya ({res_wil.execution_time_ms} ms) doit être < 50 ms"
        )

        # Test 2 : Requête par Code Wilaya
        _ = self.engine.search(wilaya="25", limit=1)
        res_code = self.engine.search(wilaya="25", limit=20)
        self.assertLess(
            res_code.execution_time_ms,
            50.0,
            f"Recherche par code wilaya ({res_code.execution_time_ms} ms) doit être < 50 ms"
        )

        # Test 3 : Détail par ID
        t0 = time.perf_counter()
        place = self.engine.get_place_by_id(res_wil.results[0]["id"])
        t1 = time.perf_counter()
        id_lookup_ms = (t1 - t0) * 1000.0
        self.assertIsNotNone(place)
        self.assertLess(id_lookup_ms, 20.0, f"Lookup par clé primaire ({id_lookup_ms} ms) doit être < 20 ms")

    def test_10_haversine_distance_accuracy(self):
        """Vérifie la formule géodésique Haversine sur des distances connues."""
        # Distance connue Alger Centre (36.7538, 3.0588) -> Blida (36.4700, 2.8277) ~ 37 km
        dist = haversine_distance(36.7538, 3.0588, 36.4700, 2.8277)
        self.assertAlmostEqual(dist, 37.5, delta=3.0)

        # Distance nulle au même point
        self.assertAlmostEqual(haversine_distance(36.75, 3.05, 36.75, 3.05), 0.0, places=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
