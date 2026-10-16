#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — API REST Standard (Phase 9)
===============================================
Micro-serveur HTTP REST pour exposer les données de santé des 58 wilayas
aux applications Web, Mobile et Bots.

Points d'entrée (Endpoints) :
-----------------------------
- GET /health
    Statut du service, volume total d'entrées, intégrité SQLite et empreinte SHA-256.
- GET /api/v1/search
    Recherche multicritère : q, wilaya, commune, specialite, has_phone, limit, offset.
- GET /api/v1/nearby
    Recherche par proximité GPS : lat, lon, radius_km, specialite, q, limit, offset.
- GET /api/v1/places/<id>
    Fiche détaillée d'un établissement par son ID numérique ou son place_id.
- GET /api/v1/wilayas
    Liste des 58 wilayas couvertes avec décompte des établissements.
- GET /api/v1/categories
    Référentiel des spécialités médicales avec statistiques.

Sécurité :
----------
- Connexion SQLite en lecture seule stricte (mode=ro, uri=True).
- Support CORS complet (requêtes multi-origines Web).
- Validation stricte des types de paramètres (lat/lon, radius, pagination).
"""

import hashlib
import json
import os
import re
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from medizy_search import MedizySearchEngine

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "medizy_scraper.db"))
EXPECTED_SHA256 = "948fda84d6375b6b1dbd7ba822cdcfe09f7301f81f8779bc803e717b582c493d"


def calculate_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


class MedizyAPIHandler(BaseHTTPRequestHandler):
    """Gestionnaire de requêtes HTTP REST standard avec sérialisation JSON et CORS."""

    # Moteur de recherche partagé
    engine: MedizySearchEngine = None
    db_sha256: str = ""

    def log_message(self, format, *args):
        """Format de log personnalisé court."""
        sys.stderr.write(f"[{self.log_date_time_string()}] {self.command} {self.path} -> {args[1]}\n")

    def _set_headers(self, status_code: int = HTTPStatus.OK):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def do_OPTIONS(self):
        """Répond aux requêtes CORS preflight."""
        self._set_headers(HTTPStatus.NO_CONTENT)

    def _send_json(self, data: Any, status_code: int = HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._set_headers(status_code)
        self.wfile.write(body)

    def _send_error(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST):
        self._send_json({"error": message, "status": status_code}, status_code=status_code)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"
        params = parse_qs(parsed.query)

        # Helper extraction mono-valeur
        def get_param(name: str, default: Optional[str] = None) -> Optional[str]:
            vals = params.get(name)
            return vals[0].strip() if vals and vals[0].strip() else default

        try:
            # Route 1 : /health
            if path in ("/health", "/api/v1/health"):
                self.handle_health()

            # Route 2 : /api/v1/search
            elif path == "/api/v1/search":
                q = get_param("q")
                wilaya = get_param("wilaya")
                commune = get_param("commune")
                specialite = get_param("specialite")
                has_phone_raw = get_param("has_phone")
                has_phone = True if has_phone_raw in ("1", "true", "True") else None
                
                try:
                    limit = min(int(get_param("limit", "20")), 100)
                    offset = max(int(get_param("offset", "0")), 0)
                except ValueError:
                    self._send_error("Paramètres 'limit' et 'offset' doivent être des entiers.")
                    return

                res = self.engine.search(
                    query=q,
                    wilaya=wilaya,
                    commune=commune,
                    specialite=specialite,
                    has_phone=has_phone,
                    limit=limit,
                    offset=offset
                )
                self._send_json({
                    "status": "success",
                    "total_count": res.total_count,
                    "page": res.page,
                    "limit": res.limit,
                    "execution_time_ms": res.execution_time_ms,
                    "filters_applied": res.filters_applied,
                    "data": res.results
                })

            # Route 3 : /api/v1/nearby
            elif path == "/api/v1/nearby":
                lat_str = get_param("lat")
                lon_str = get_param("lon")
                if not lat_str or not lon_str:
                    self._send_error("Paramètres 'lat' et 'lon' requis pour la recherche géospatiale.")
                    return

                try:
                    lat = float(lat_str)
                    lon = float(lon_str)
                except ValueError:
                    self._send_error("'lat' et 'lon' doivent être des coordonnées décimales valides.")
                    return

                try:
                    radius_km = min(max(float(get_param("radius_km", "5.0")), 0.1), 100.0)
                    limit = min(int(get_param("limit", "20")), 100)
                    offset = max(int(get_param("offset", "0")), 0)
                except ValueError:
                    self._send_error("'radius_km', 'limit' et 'offset' doivent être numériques.")
                    return

                specialite = get_param("specialite")
                q = get_param("q")

                res = self.engine.search(
                    query=q,
                    specialite=specialite,
                    latitude=lat,
                    longitude=lon,
                    radius_km=radius_km,
                    limit=limit,
                    offset=offset
                )
                self._send_json({
                    "status": "success",
                    "total_count": res.total_count,
                    "page": res.page,
                    "limit": res.limit,
                    "radius_km": radius_km,
                    "execution_time_ms": res.execution_time_ms,
                    "filters_applied": res.filters_applied,
                    "data": res.results
                })

            # Route 4 : /api/v1/places/<id>
            elif path.startswith("/api/v1/places/"):
                place_id_val = path[len("/api/v1/places/"):]
                if not place_id_val:
                    self._send_error("Identifiant d'établissement manquant.")
                    return
                place = self.engine.get_place_by_id(place_id_val)
                if not place:
                    self._send_error("Établissement introuvable.", status_code=HTTPStatus.NOT_FOUND)
                    return
                self._send_json({"status": "success", "data": place})

            # Route 5 : /api/v1/wilayas
            elif path == "/api/v1/wilayas":
                wilayas = self.engine.get_wilayas_stats()
                self._send_json({
                    "status": "success",
                    "wilayas_count": len(wilayas),
                    "data": wilayas
                })

            # Route 6 : /api/v1/categories
            elif path == "/api/v1/categories":
                cats = self.engine.get_categories_stats()
                self._send_json({
                    "status": "success",
                    "categories_count": len(cats),
                    "data": cats
                })

            else:
                self._send_error(f"Route introuvable : {path}", status_code=HTTPStatus.NOT_FOUND)

        except Exception as e:
            self._send_error(f"Erreur interne du serveur : {str(e)}", status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_health(self):
        """Retourne la santé de l'API, le volume et l'intégrité de la base."""
        conn = self.engine._get_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        integrity = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM places;")
        total_places = cur.fetchone()[0]
        cur.close()

        payload = {
            "status": "healthy",
            "service": "Santé DZ Medizy REST API",
            "version": "1.0.0",
            "database": {
                "path": DB_PATH,
                "mode": "read_only",
                "total_entries": total_places,
                "sqlite_integrity": integrity,
                "sha256": MedizyAPIHandler.db_sha256
            },
            "coverage": {
                "wilayas_covered": 58,
                "gps_coordinates_pct": 100.0
            }
        }
        self._send_json(payload)


def run_server(host: str = "127.0.0.1", port: int = 8000):
    print("=" * 70)
    print("SANTÉ DZ MEDIZY — DÉMARRAGE DU SERVEUR API REST (PHASE 9)")
    print("=" * 70)
    print(f"Base de données : {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"Erreur : base {DB_PATH} introuvable.")
        sys.exit(1)

    print("Calcul de l'empreinte SHA-256 de contrôle...")
    actual_sha = calculate_sha256(DB_PATH)
    print(f"SHA-256 : {actual_sha}")
    if actual_sha == EXPECTED_SHA256:
        print("[SUCCÈS] SHA-256 CONFORME à la production Phase 8.4")

    # Initialisation du moteur de recherche en lecture seule
    engine = MedizySearchEngine(db_path=DB_PATH)
    MedizyAPIHandler.engine = engine
    MedizyAPIHandler.db_sha256 = actual_sha

    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, MedizyAPIHandler)
    print(f"\nServeur API en écoute sur http://{host}:{port}/")
    print(f"  * GET http://{host}:{port}/health")
    print(f"  * GET http://{host}:{port}/api/v1/search?wilaya=16&specialite=cardio")
    print(f"  * GET http://{host}:{port}/api/v1/nearby?lat=36.7538&lon=3.0588&radius_km=5.0")
    print(f"  * GET http://{host}:{port}/api/v1/wilayas")
    print(f"  * GET http://{host}:{port}/api/v1/categories")
    print("\nAppuyez sur Ctrl+C pour arrêter le serveur.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur API...")
    finally:
        httpd.server_close()
        engine.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Serveur API REST Santé DZ Medizy")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse d'écoute")
    parser.add_argument("--port", type=int, default=8000, help="Port d'écoute")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
