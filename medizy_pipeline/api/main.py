#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Application FastAPI Principale (Production-Ready)
=====================================================================
Point d'entrée du microservice d'établissements de santé et recherche géospatiale.
Expose la documentation interactive Swagger UI sur `/docs` et OpenAPI sur `/openapi.json`.
Gère le cycle de vie (lifespan) pour le pool de connexions SQL et la configuration CORS/Sécurité.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Header, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from .db import close_db_service, get_db_service
from .routes.facilities import router as facilities_router
from .routes.suggestions import router as suggestions_router
from .routes.admin_moderation import router as admin_moderation_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("medizy.api")

# Configuration Sécurité & Clé API optionnelle
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_cors_origins() -> List[str]:
    """Parse la variable d'environnement CORS_ORIGINS (séparateur virgule) ou autorise tout par défaut."""
    env_origins = os.environ.get("CORS_ORIGINS", "*").strip()
    if env_origins == "*":
        return ["*"]
    return [origin.strip() for origin in env_origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire du cycle de vie de l'application FastAPI :
      - Initialise le pool de connexions SQL au démarrage.
      - Libère et ferme proprement le pool lors de l'arrêt du serveur.
    """
    logger.info("=== Initialisation du service API MEDIZY ===")
    db = get_db_service()
    backend = "PostgreSQL / PostGIS" if db.is_postgres else f"SQLite Local ({db.sqlite_path})"
    logger.info(f"Base de données connectée : {backend}")

    yield

    logger.info("=== Arrêt du service API MEDIZY ===")
    close_db_service()
    logger.info("Ressources libérées avec succès.")


app = FastAPI(
    title="MEDIZY / SANTÉ DZ — API Établissements de Santé",
    version="2.0.0",
    description="""
    Plateforme nationale d'accès et d'enrichissement cartographique des structures de santé
    (CHU, EPH, EPSP, Cliniques, Polycliniques, Urgences) sur l'ensemble des 58 wilayas d'Algérie.

    **Fonctionnalités clés :**
    * **Recherche géospatiale haute performance** : requêtes par rayon métrique (`ST_DWithin`) ou bounding box cartographique.
    * **Visibilité complète** : intégration sans exclusion des fiches publiques non revendiquées (`is_claimed = false`).
    * **Crowdsourcing & Modération** : soumission citoyenne avec extraction automatique de coordonnées depuis liens Google Maps.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configuration CORS pour autoriser l'accès depuis l'application mobile Flutter et le frontend Web
origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def read_only_mode_middleware(request, call_next):
    """
    Intercepte les requêtes d'écriture en mode maintenance / lecture seule.
    Permet de geler immédiatement les mutations (suggestions citoyennes, modérations)
    pendant les opérations d'infrastructure ou de sauvegarde sans interrompre les lectures.
    """
    is_read_only = os.environ.get("READ_ONLY_MODE", "false").lower() in ("true", "1", "yes")
    if is_read_only and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "READ_ONLY_MODE",
                "status": "maintenance",
                "message": (
                    "La plateforme MEDIZY est temporairement en mode lecture seule pour maintenance d'infrastructure. "
                    "Les écritures (suggestions, modérations) sont suspendues."
                ),
            },
        )
    return await call_next(request)


# Inclusion des routeurs modulaires
app.include_router(facilities_router)
app.include_router(suggestions_router)
app.include_router(admin_moderation_router)

# Instrumentation Prometheus & Métriques (/metrics)
from .metrics import setup_prometheus_instrumentator
setup_prometheus_instrumentator(app)


@app.get("/health", tags=["Système"])
def health_check():
    """Vérification de l'état de fonctionnement de l'API et de la connexion base de données."""
    db = get_db_service()
    is_read_only = os.environ.get("READ_ONLY_MODE", "false").lower() in ("true", "1", "yes")
    return {
        "status": "healthy",
        "service": "medizy-facilities-api",
        "mode": "read_only" if is_read_only else "read_write",
        "database_backend": "PostgreSQL/PostGIS" if db.is_postgres else "SQLite (Local Mode)",
        "version": "2.0.0",
        "cors_origins": origins,
    }



if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("medizy_pipeline.api.main:app", host=host, port=port, reload=True)
