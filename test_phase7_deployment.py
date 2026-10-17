#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SANTÉ DZ / MEDIZY — TESTS DE DÉPLOIEMENT PHASE 7
================================================
Validation automatisée de la conteneurisation Docker, des services natifs
multi-environnements (Systemd & Windows Service), et du moniteur de santé / autoréparation.
"""

import json
import os
import re
import sys
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer

from api_server import MedizyAPIHandler, calculate_sha256, DB_PATH
from medizy_search import MedizySearchEngine
from tools.health_monitor import MedizyHealthMonitor, HealthCheckResult

TEST_HOST = "127.0.0.1"
TEST_PORT = 8897


class TestPhase7Deployment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Démarre une instance de test du serveur API en tâche de fond."""
        cls.engine = MedizySearchEngine(db_path=DB_PATH)
        MedizyAPIHandler.engine = cls.engine
        MedizyAPIHandler.db_sha256 = calculate_sha256(DB_PATH)

        cls.httpd = ThreadingHTTPServer((TEST_HOST, TEST_PORT), MedizyAPIHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)
        # Préchauffage du serveur pour initialiser les sockets et les caches SQLite
        try:
            import urllib.request
            urllib.request.urlopen(f"http://{TEST_HOST}:{TEST_PORT}/api/v1/health", timeout=2)
            urllib.request.urlopen(f"http://{TEST_HOST}:{TEST_PORT}/api/v1/stats", timeout=2)
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        """Arrête le serveur HTTP de test."""
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.engine.close()

    def test_01_dockerfile_compliance(self):
        """Vérifie la conformité et la sécurité du Dockerfile."""
        dockerfile_path = os.path.join(os.path.dirname(__file__), "deployment", "Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path), "deployment/Dockerfile manquant")

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Image de base ultra-légère
        self.assertIn("FROM python:3.11-slim", content)

        # Utilisateur non-root non privilégié
        self.assertRegex(content, r"useradd.*medizy", "Utilisateur non-root non créé")
        self.assertIn("USER medizy", content)

        # Port 8000 exposé
        self.assertIn("EXPOSE 8000", content)

        # Healthcheck natif sans outil tiers
        self.assertIn("HEALTHCHECK", content)
        self.assertIn("/api/v1/health", content)

        # Exécution en lecture seule de la base
        self.assertIn("MEDIZY_DB_PATH=/app/medizy_scraper.db", content)

    def test_02_docker_compose_compliance(self):
        """Vérifie la configuration des ressources et volumes dans docker-compose.yml."""
        compose_path = os.path.join(os.path.dirname(__file__), "deployment", "docker-compose.yml")
        self.assertTrue(os.path.exists(compose_path), "deployment/docker-compose.yml manquant")

        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("medizy-api:", content)
        self.assertIn("restart: always", content)

        # Limitation stricte des ressources
        self.assertRegex(content, r"cpus:\s*['\"]?0\.5", "Limite CPU 0.5 manquante")
        self.assertRegex(content, r"memory:\s*256M", "Limite RAM 256M manquante")

        # Montage SQLite en lecture seule (:ro)
        self.assertIn("./medizy_scraper.db:/app/medizy_scraper.db:ro", content)
        self.assertIn('"8000:8000"', content)

    def test_03_systemd_service_compliance(self):
        """Vérifie la définition de l'unité systemd pour VPS Linux."""
        service_path = os.path.join(os.path.dirname(__file__), "deployment", "medizy.service")
        self.assertTrue(os.path.exists(service_path), "deployment/medizy.service manquant")

        with open(service_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("[Unit]", content)
        self.assertIn("[Service]", content)
        self.assertIn("[Install]", content)
        self.assertIn("Restart=always", content)
        self.assertIn("PORT=8000", content)
        self.assertIn("User=medizy", content)
        self.assertIn("ExecStart=", content)

    def test_04_windows_service_compliance(self):
        """Vérifie le script PowerShell de gestion du service d'arrière-plan Windows."""
        ps1_path = os.path.join(os.path.dirname(__file__), "deployment", "start_windows_service.ps1")
        self.assertTrue(os.path.exists(ps1_path), "deployment/start_windows_service.ps1 manquant")

        with open(ps1_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn(r"D:\SANTE_DZ_EXPORTS\logs", content)
        self.assertIn("api_service.log", content)
        self.assertIn("api_service.pid", content)
        self.assertIn("WindowStyle Hidden", content)
        self.assertIn("start", content)
        self.assertIn("stop", content)
        self.assertIn("status", content)
        self.assertIn("restart", content)

    def test_05_health_monitor_healthy_instance(self):
        """Vérifie que health_monitor valide avec succès une instance saine."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_report_path = tmp_file.name

        try:
            monitor = MedizyHealthMonitor(
                base_url=f"http://{TEST_HOST}:{TEST_PORT}",
                max_latency_ms=250.0,
                report_file=tmp_report_path,
                auto_restart=False,
            )

            # Test check_health
            h_res = monitor.check_health()
            self.assertEqual(h_res.status, "OK")
            self.assertEqual(h_res.status_code, 200)
            self.assertEqual(h_res.details.get("sqlite_integrity"), "ok")
            self.assertGreaterEqual(h_res.details.get("total_entries", 0), 30000)

            # Test check_stats
            s_res = monitor.check_stats()
            self.assertEqual(s_res.status, "OK")
            self.assertEqual(s_res.status_code, 200)
            self.assertEqual(s_res.details.get("wilayas_covered"), 58)

            # Test check_cache
            c_res = monitor.check_cache()
            self.assertEqual(c_res.status, "OK")
            self.assertEqual(c_res.status_code, 200)

            # Test run_cycle
            report = monitor.run_cycle()
            self.assertEqual(report["overall_status"], "HEALTHY")
            self.assertEqual(report["critical_incidents"], 0)
            self.assertEqual(report["warning_incidents"], 0)
            self.assertLess(report["average_latency_ms"], 250.0)

            # Vérification du fichier rapport JSON généré
            self.assertTrue(os.path.exists(tmp_report_path))
            with open(tmp_report_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["overall_status"], "HEALTHY")
            self.assertIn("checks", saved)

        finally:
            if os.path.exists(tmp_report_path):
                os.remove(tmp_report_path)

    def test_06_health_monitor_unavailable_instance(self):
        """Vérifie le comportement du moniteur sur une instance indisponible."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_report_path = tmp_file.name

        try:
            # Port non ouvert
            monitor = MedizyHealthMonitor(
                base_url="http://127.0.0.1:59999",
                max_latency_ms=200.0,
                report_file=tmp_report_path,
                auto_restart=False,
            )

            report = monitor.run_cycle()
            self.assertEqual(report["overall_status"], "DOWN")
            self.assertGreater(report["critical_incidents"], 0)
            self.assertEqual(report["checks"]["health"]["status"], "CRITICAL")
            self.assertIn("Échec de connexion", report["checks"]["health"]["message"])

        finally:
            if os.path.exists(tmp_report_path):
                os.remove(tmp_report_path)

    def test_07_health_monitor_high_latency_warning(self):
        """Vérifie la détection de dégradation de performance par dépassement de seuil."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_report_path = tmp_file.name

        try:
            # Seuil quasi-nul (0.0001 ms) pour simuler une latence anormale
            monitor = MedizyHealthMonitor(
                base_url=f"http://{TEST_HOST}:{TEST_PORT}",
                max_latency_ms=0.0001,
                report_file=tmp_report_path,
                auto_restart=False,
            )

            report = monitor.run_cycle()
            self.assertEqual(report["overall_status"], "DEGRADED")
            self.assertGreater(report["warning_incidents"], 0)
            self.assertEqual(report["critical_incidents"], 0)

        finally:
            if os.path.exists(tmp_report_path):
                os.remove(tmp_report_path)


if __name__ == "__main__":
    unittest.main()
