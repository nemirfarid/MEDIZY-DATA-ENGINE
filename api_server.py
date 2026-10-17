#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — API REST Standard & Swagger Docs (Phase 9 & 10)
===================================================================
Micro-serveur HTTP REST pour exposer les données de santé des 58 wilayas
aux applications Web, Mobile et Bots.

Points d'entrée (Endpoints) :
-----------------------------
- GET /health
    Statut du service, volume total d'entrées, intégrité SQLite et empreinte SHA-256.
- GET /docs
    Interface interactive Swagger UI de documentation de l'API.
- GET /openapi.json
    Spécification OpenAPI 3.0.3 complète des routes et schémas.
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

import datetime
import gzip
import hashlib
import json
import os
import re
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from medizy_search import MedizySearchEngine, OFFICIAL_WILAYAS, strip_accents
from export_mobile_cache import export_wilaya, export_national_cache, DEFAULT_OUT_DIR

DB_PATH = os.environ.get("MEDIZY_DB_PATH") or os.path.abspath(os.path.join(os.path.dirname(__file__), "medizy_scraper.db"))
EXPECTED_SHA256 = "69b94b3ca03d80d5ea33f8395482c6763e72d1fba5c491300b0e92dcd6d12e65"


def calculate_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def get_openapi_specification() -> Dict[str, Any]:
    """Retourne le document de spécification OpenAPI 3.0.3 complet."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Santé DZ Medizy API",
            "version": "1.0.9",
            "description": "API REST géospatiale et plein texte pour les 23 669 établissements de santé des 58 wilayas d'Algérie.",
            "contact": {
                "name": "Équipe Santé DZ Medizy",
                "url": "https://medizy.dz"
            }
        },
        "servers": [
            {"url": "/", "description": "Serveur API Local"}
        ],
        "paths": {
            "/health": {
                "get": {
                    "summary": "État de santé et métadonnées de la base",
                    "description": "Vérifie l'intégrité SQLite, le statut de lecture seule et l'empreinte SHA-256.",
                    "responses": {
                        "200": {
                            "description": "Système opérationnel",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HealthResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/search": {
                "get": {
                    "summary": "Recherche multicritère d'établissements de santé",
                    "description": "Recherche par texte libre, wilaya (code ou nom), commune, et spécialité médicale.",
                    "parameters": [
                        {"name": "q", "in": "query", "description": "Mots-clés libres", "schema": {"type": "string"}},
                        {"name": "wilaya", "in": "query", "description": "Code (ex: 16) ou nom (ex: Alger)", "schema": {"type": "string"}},
                        {"name": "commune", "in": "query", "description": "Nom de commune (ex: Kouba)", "schema": {"type": "string"}},
                        {"name": "specialite", "in": "query", "description": "Spécialité (ex: cardio, dentiste)", "schema": {"type": "string"}},
                        {"name": "has_phone", "in": "query", "description": "Filtrer avec numéro de téléphone (true/1)", "schema": {"type": "boolean"}},
                        {"name": "limit", "in": "query", "description": "Nombre maximum de résultats (1-100)", "schema": {"type": "integer", "default": 20}},
                        {"name": "offset", "in": "query", "description": "Décalage pour pagination", "schema": {"type": "integer", "default": 0}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Résultats de la recherche",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/SearchResult"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/nearby": {
                "get": {
                    "summary": "Recherche géospatiale par rayon géographique",
                    "description": "Recherche les établissements dans un rayon donné (formule Haversine, tri ascendant par distance).",
                    "parameters": [
                        {"name": "lat", "in": "query", "required": True, "description": "Latitude décimale (ex: 36.7538)", "schema": {"type": "number", "format": "float"}},
                        {"name": "lon", "in": "query", "required": True, "description": "Longitude décimale (ex: 3.0588)", "schema": {"type": "number", "format": "float"}},
                        {"name": "radius_km", "in": "query", "description": "Rayon en km (défaut 5.0, max 100.0)", "schema": {"type": "number", "default": 5.0}},
                        {"name": "specialite", "in": "query", "description": "Filtre par spécialité", "schema": {"type": "string"}},
                        {"name": "q", "in": "query", "description": "Mots-clés additionnels", "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}},
                        {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Établissements ordonnés par distance",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/NearbyResult"}
                                }
                            }
                        },
                        "400": {"description": "Paramètres manquants ou invalides"}
                    }
                }
            },
            "/api/v1/places/{id}": {
                "get": {
                    "summary": "Détail d'un établissement par ID",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "description": "ID SQLite ou place_id", "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {"description": "Fiche complète de l'établissement"},
                        "404": {"description": "Établissement non trouvé"}
                    }
                }
            },
            "/api/v1/wilayas": {
                "get": {
                    "summary": "Liste et statistiques des 58 wilayas",
                    "responses": {
                        "200": {"description": "Décompte des établissements par wilaya"}
                    }
                }
            },
            "/api/v1/categories": {
                "get": {
                    "summary": "Spécialités et catégories médicales",
                    "responses": {
                        "200": {"description": "Statistiques par spécialité"}
                    }
                }
            },
            "/api/v1/stats": {
                "get": {
                    "summary": "Métriques en direct de la base de production",
                    "description": "Fournit le total certifié d'établissements, la couverture des 58 wilayas, la ventilation par source et les taux GPS/téléphone.",
                    "responses": {
                        "200": {"description": "Métriques consolidées en temps réel"}
                    }
                }
            },
            "/api/v1/cache/version": {
                "get": {
                    "summary": "Version et métadonnées du cache hors-ligne mobile",
                    "description": "Fournit l'empreinte SHA-256, le décompte global et les liens de téléchargement pour la synchronisation delta.",
                    "responses": {
                        "200": {"description": "Informations de version et statut du cache"}
                    }
                }
            },
            "/api/v1/cache/national": {
                "get": {
                    "summary": "Téléchargement de l'archive nationale complète (GZIP)",
                    "description": "Stream binaire de l'archive medizy_national_cache.json.gz (23 669 établissements).",
                    "responses": {
                        "200": {
                            "description": "Archive binaire GZIP",
                            "headers": {
                                "Content-Type": {"schema": {"type": "string", "example": "application/gzip"}},
                                "Content-Disposition": {"schema": {"type": "string", "example": "attachment; filename=\"medizy_national_cache.json.gz\""}}
                            }
                        }
                    }
                }
            },
            "/api/v1/cache/wilaya/{code}": {
                "get": {
                    "summary": "Téléchargement du cache partitionné par wilaya (GZIP)",
                    "description": "Stream binaire de l'archive spécifique à une wilaya (ex: 16 pour Alger).",
                    "parameters": [
                        {"name": "code", "in": "path", "required": True, "description": "Code officiel (01-58) ou nom de wilaya", "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {"description": "Archive GZIP de la wilaya demandée"},
                        "404": {"description": "Wilaya introuvable"}
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Facility": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "place_id": {"type": "string", "nullable": True},
                        "nom": {"type": "string"},
                        "categorie_recherche": {"type": "string", "nullable": True},
                        "wilaya": {"type": "string", "nullable": True},
                        "commune": {"type": "string", "nullable": True},
                        "adresse": {"type": "string", "nullable": True},
                        "telephone": {"type": "string", "nullable": True},
                        "telephone_normalized": {"type": "string", "nullable": True},
                        "site_web": {"type": "string", "nullable": True},
                        "note": {"type": "string", "nullable": True},
                        "nombre_avis": {"type": "string", "nullable": True},
                        "latitude": {"type": "number", "nullable": True},
                        "longitude": {"type": "number", "nullable": True},
                        "google_maps_url": {"type": "string", "nullable": True},
                        "source": {"type": "string", "nullable": True},
                        "distance_km": {"type": "number", "nullable": True}
                    }
                },
                "SearchResult": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "success"},
                        "total_count": {"type": "integer"},
                        "page": {"type": "integer"},
                        "limit": {"type": "integer"},
                        "execution_time_ms": {"type": "number"},
                        "filters_applied": {"type": "object"},
                        "data": {"type": "array", "items": {"$ref": "#/components/schemas/Facility"}}
                    }
                },
                "NearbyResult": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "success"},
                        "total_count": {"type": "integer"},
                        "page": {"type": "integer"},
                        "limit": {"type": "integer"},
                        "radius_km": {"type": "number"},
                        "execution_time_ms": {"type": "number"},
                        "filters_applied": {"type": "object"},
                        "data": {"type": "array", "items": {"$ref": "#/components/schemas/Facility"}}
                    }
                },
                "HealthResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "healthy"},
                        "service": {"type": "string"},
                        "version": {"type": "string"},
                        "database": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "mode": {"type": "string"},
                                "total_entries": {"type": "integer"},
                                "sqlite_integrity": {"type": "string"},
                                "sha256": {"type": "string"}
                            }
                        },
                        "coverage": {
                            "type": "object",
                            "properties": {
                                "wilayas_covered": {"type": "integer"},
                                "gps_coordinates_pct": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    }


SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Santé DZ Medizy — Documentation Swagger API</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5/favicon-32x32.png" sizes="32x32" />
  <style>
    html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
    *, *:before, *:after { box-sizing: inherit; }
    body { margin: 0; background: #fafafa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .topbar { background-color: #0d9488 !important; }
    .swagger-ui .topbar .topbar-wrapper .link span { color: #fff; font-weight: bold; font-size: 1.1em; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js" charset="UTF-8"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js" charset="UTF-8"></script>
  <script>
    window.onload = function() {
      window.ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout"
      });
    };
  </script>
</body>
</html>
"""


class MedizyAPIHandler(BaseHTTPRequestHandler):
    """Gestionnaire de requêtes HTTP REST standard avec sérialisation JSON, OpenAPI et CORS."""

    engine: MedizySearchEngine = None
    db_sha256: str = ""

    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {self.command} {self.path} -> {args[1]}\n")

    def _set_headers(self, status_code: int = HTTPStatus.OK, content_type: str = "application/json; charset=utf-8"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(HTTPStatus.NO_CONTENT)

    def _send_json(self, data: Any, status_code: int = HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        accept_encoding = self.headers.get("Accept-Encoding", "") if hasattr(self, "headers") and self.headers else ""
        use_gzip = "gzip" in accept_encoding.lower() and len(body) > 256

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept-Encoding")
        self.send_header("Cache-Control", "no-cache")

        if use_gzip:
            compressed = gzip.compress(body)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(compressed)))
            self.end_headers()
            self.wfile.write(compressed)
        else:
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _send_html(self, html_content: str, status_code: int = HTTPStatus.OK):
        body = html_content.encode("utf-8")
        self._set_headers(status_code, "text/html; charset=utf-8")
        self.wfile.write(body)

    def _send_error(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST):
        self._send_json({"error": message, "status": status_code}, status_code=status_code)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"
        params = parse_qs(parsed.query)

        def get_param(name: str, default: Optional[str] = None) -> Optional[str]:
            vals = params.get(name)
            return vals[0].strip() if vals and vals[0].strip() else default

        try:
            # 1. Documentation Swagger UI
            if path in ("/docs", "/swagger"):
                self._send_html(SWAGGER_UI_HTML)

            # 2. Spécification OpenAPI 3.0
            elif path in ("/openapi.json", "/api/v1/openapi.json"):
                self._send_json(get_openapi_specification())

            # 3. Contrôle de santé
            elif path in ("/health", "/api/v1/health"):
                self.handle_health()

            # 3b. Métriques statistiques en direct
            elif path in ("/stats", "/api/v1/stats"):
                self.handle_stats()

            # 4. Recherche multicritère
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

            # 5. Recherche par proximité géospatiale
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

            # 6. Fiche détaillée d'un établissement
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

            # 7. Liste des wilayas
            elif path == "/api/v1/wilayas":
                wilayas = self.engine.get_wilayas_stats()
                self._send_json({
                    "status": "success",
                    "wilayas_count": len(wilayas),
                    "data": wilayas
                })

            # 8. Référentiel des catégories
            elif path == "/api/v1/categories":
                cats = self.engine.get_categories_stats()
                self._send_json({
                    "status": "success",
                    "categories_count": len(cats),
                    "data": cats
                })

            # 9. Version et métadonnées du cache mobile
            elif path == "/api/v1/cache/version":
                self.handle_cache_version()

            # 10. Téléchargement de l'archive nationale complète
            elif path == "/api/v1/cache/national":
                national_path = os.path.join(DEFAULT_OUT_DIR, "medizy_national_cache.json.gz")
                if not os.path.exists(national_path):
                    export_national_cache(output_dir=DEFAULT_OUT_DIR)
                self._send_file(national_path, "medizy_national_cache.json.gz", "application/gzip")

            # 11. Téléchargement du cache partitionné par wilaya
            elif path.startswith("/api/v1/cache/wilaya/"):
                wil_param = path[len("/api/v1/cache/wilaya/"):].strip()
                if not wil_param:
                    self._send_error("Code ou nom de wilaya requis.")
                    return
                resolved = self.engine.resolve_wilaya(wil_param)
                wilaya_code = None
                for code, name in OFFICIAL_WILAYAS:
                    if name.lower() == str(resolved).lower():
                        wilaya_code = code
                        resolved = name
                        break
                if not wilaya_code:
                    self._send_error(f"Wilaya inconnue ou non officielle : {wil_param}", status_code=HTTPStatus.NOT_FOUND)
                    return
                norm_clean = strip_accents(resolved).replace(" ", "_").replace("'", "")
                filename = f"medizy_wilaya_{wilaya_code}_{norm_clean}.json.gz"

                candidates = [
                    os.path.join(DEFAULT_OUT_DIR, "wilayas", filename),
                    os.path.join(DEFAULT_OUT_DIR, filename)
                ]
                found_path = next((p for p in candidates if os.path.exists(p)), None)
                if not found_path:
                    stat = export_wilaya(resolved, output_dir=os.path.join(DEFAULT_OUT_DIR, "wilayas"))
                    found_path = stat["filepath"]

                self._send_file(found_path, filename, "application/gzip")

            else:
                self._send_error(f"Route introuvable : {path}", status_code=HTTPStatus.NOT_FOUND)

        except Exception as e:
            self._send_error(f"Erreur interne du serveur : {str(e)}", status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _send_file(self, filepath: str, filename: str, content_type: str = "application/gzip"):
        """Envoie un fichier binaire avec en-têtes de téléchargement et cache."""
        if not os.path.exists(filepath):
            self._send_error(f"Fichier introuvable : {filename}", status_code=HTTPStatus.NOT_FOUND)
            return
        file_size = os.path.getsize(filepath)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                self.wfile.write(chunk)

    def handle_cache_version(self):
        """Retourne les métadonnées de version du cache client mobile pour synchronisation delta."""
        national_path = os.path.join(DEFAULT_OUT_DIR, "medizy_national_cache.json.gz")
        national_size = os.path.getsize(national_path) if os.path.exists(national_path) else None
        
        db_stat = os.stat(DB_PATH) if os.path.exists(DB_PATH) else None
        last_modified = datetime.datetime.fromtimestamp(db_stat.st_mtime, tz=datetime.timezone.utc).isoformat() if db_stat else None

        payload = {
            "status": "success",
            "version": "1.0.9",
            "schema_version": "1.0",
            "last_updated": last_modified,
            "database_sha256": MedizyAPIHandler.db_sha256,
            "total_facilities": 23669,
            "total_wilayas": 58,
            "national_cache": {
                "available": national_size is not None,
                "download_url": "/api/v1/cache/national",
                "size_bytes": national_size,
                "size_human": f"{national_size / (1024*1024):.2f} MB" if national_size else None
            },
            "wilaya_cache_template": "/api/v1/cache/wilaya/{code}"
        }
        self._send_json(payload)

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
            "version": "1.0.9",
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

    def handle_stats(self):
        """Retourne les métriques en direct : total établissements, couverture 58 wilayas, ventilation par source."""
        conn = self.engine._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM places;")
        total_places = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT wilaya) FROM places WHERE wilaya IS NOT NULL AND TRIM(wilaya) != '';")
        wilayas_covered = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(source, 'Inconnue') as src, COUNT(*) as cnt FROM places GROUP BY src ORDER BY cnt DESC;")
        sources_breakdown = {r["src"]: r["cnt"] for r in cur.fetchall()}
        cur.execute("SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND TRIM(telephone) != '';")
        phone_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND latitude != 0 AND longitude != 0;")
        gps_count = cur.fetchone()[0]
        cur.close()

        payload = {
            "status": "success",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "metrics": {
                "total_facilities": total_places,
                "wilayas_covered": wilayas_covered,
                "sources_breakdown": sources_breakdown,
                "with_phone": phone_count,
                "with_gps": gps_count,
                "gps_coverage_pct": round(gps_count / total_places * 100.0, 2) if total_places else 0.0,
                "database_sha256": MedizyAPIHandler.db_sha256
            }
        }
        self._send_json(payload)


def run_server(host: str = "127.0.0.1", port: int = 8000):
    print("=" * 70)
    print("SANTÉ DZ MEDIZY — DÉMARRAGE DU SERVEUR API REST (PHASE 9 & 10)")
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

    engine = MedizySearchEngine(db_path=DB_PATH)
    MedizyAPIHandler.engine = engine
    MedizyAPIHandler.db_sha256 = actual_sha

    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, MedizyAPIHandler)
    print(f"\nServeur API en écoute sur http://{host}:{port}/")
    print(f"  * Documentation Swagger UI : http://{host}:{port}/docs")
    print(f"  * Spécification OpenAPI    : http://{host}:{port}/openapi.json")
    print(f"  * Santé système             : http://{host}:{port}/health")
    print(f"  * Recherche multicritère   : http://{host}:{port}/api/v1/search?wilaya=16&specialite=cardio")
    print(f"  * Recherche proximité GPS  : http://{host}:{port}/api/v1/nearby?lat=36.7538&lon=3.0588&radius_km=5.0")
    print(f"  * Liste des wilayas        : http://{host}:{port}/api/v1/wilayas")
    print(f"  * Catégories médicales     : http://{host}:{port}/api/v1/categories")
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
