#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Métriques & Observabilité Prometheus / Grafana
=================================================================
Instrumentation applicative exposant `/metrics` pour Prometheus.
Suivi en temps réel des RPS géospatiaux, latences p95/p99, volume de
suggestions citoyennes et incidents de basculement de miroirs Overpass.
"""

import logging
import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger("medizy.metrics")

# ==============================================================================
# 1. MÉTRIQUES MÉTIER & GÉOSPATIALES MEDIZY
# ==============================================================================

# Latence détaillée des recherches spatiales (/nearby, /search)
geosearch_duration_seconds = Histogram(
    "medizy_geosearch_duration_seconds",
    "Durée d'exécution des recherches géospatiales (/nearby, /search) en secondes",
    ["endpoint", "type_filter", "wilaya"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0),
)

# Compteur de requêtes spatiales
geosearch_requests_total = Counter(
    "medizy_geosearch_requests_total",
    "Nombre total de requêtes spatiales reçues par l'API",
    ["endpoint", "status"],
)

# Jauge du volume de suggestions citoyennes en attente de modération
pending_suggestions_gauge = Gauge(
    "pending_suggestions_gauge",
    "Nombre actuel de suggestions citoyennes en attente de validation administrative (statut PENDING)",
)

# Compteur d'incidents de bascule de miroirs OSM Overpass
osm_mirror_failover_total = Counter(
    "osm_mirror_failover_total",
    "Nombre total de basculements de miroirs OSM Overpass suite à un timeout réseau ou indisponibilité",
    ["wilaya", "target_mirror"],
)

# Compteur de synchronisations vers l'écosystème IA (NIBRAS)
nibras_sync_exports_total = Counter(
    "medizy_nibras_sync_exports_total",
    "Nombre total d'extractions incrémentales de structures de santé pour l'index sémantique NIBRAS",
    ["status"],
)


# Métriques de surveillance et fraîcheur des sauvegardes PostGIS
medizy_last_backup_timestamp = Gauge(
    "medizy_last_backup_timestamp",
    "Timestamp Unix de la dernière sauvegarde PostGIS certifiée valide",
)

medizy_backup_success_status = Gauge(
    "medizy_backup_success_status",
    "Statut de conformité de la sauvegarde (1 = archive < 26h et intègre, 0 = manquante ou corrompue)",
)


# ==============================================================================
# 2. FONCTIONS DE MISE À JOUR DES MÉTRIQUES
# ==============================================================================

def record_geosearch_metrics(endpoint: str, duration_seconds: float, type_filter: Optional[str] = None, wilaya: Optional[str] = None, status: str = "success"):
    """Enregistre la latence et l'occurrence d'une requête géospatiale."""
    try:
        geosearch_duration_seconds.labels(
            endpoint=endpoint,
            type_filter=type_filter or "all",
            wilaya=wilaya or "all",
        ).observe(duration_seconds)
        geosearch_requests_total.labels(endpoint=endpoint, status=status).inc()
    except Exception as e:
        logger.debug(f"Erreur enregistrement métrique spatiale: {e}")


def record_mirror_failover(wilaya: str, target_mirror: str):
    """Incrémente le compteur d'incidents de basculement de miroir OSM Overpass."""
    try:
        osm_mirror_failover_total.labels(
            wilaya=wilaya or "algerie",
            target_mirror=target_mirror,
        ).inc()
    except Exception as e:
        logger.debug(f"Erreur enregistrement failover miroir: {e}")


def update_pending_suggestions_gauge():
    """Interroge la base de données pour mettre à jour la jauge des suggestions en attente."""
    try:
        from .db import get_db_service
        db = get_db_service()
        total, _ = db.list_suggestions(status="PENDING", limit=1, offset=0)
        pending_suggestions_gauge.set(total)
    except Exception as e:
        logger.debug(f"Erreur mise à jour jauge suggestions: {e}")


def update_backup_freshness_gauge():
    """Vérifie la fraîcheur de la dernière sauvegarde PostGIS locale ou fichier d'état."""
    try:
        import glob
        import json
        import os
        backup_dir = os.environ.get("BACKUP_DIR", "/var/backups/medizy")
        state_file = os.environ.get("BACKUP_STATE_FILE", os.path.join(backup_dir, "backup_state.json"))

        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                medizy_last_backup_timestamp.set(float(data.get("last_backup_timestamp", 0)))
                medizy_backup_success_status.set(1.0 if data.get("is_valid") else 0.0)
                return
            except Exception:
                pass

        if os.path.isdir(backup_dir):
            dump_files = glob.glob(os.path.join(backup_dir, "*.dump"))
            if dump_files:
                newest = max(dump_files, key=os.path.getmtime)
                mtime = os.path.getmtime(newest)
                age = time.time() - mtime
                is_fresh = 1.0 if age <= 26 * 3600 else 0.0
                medizy_last_backup_timestamp.set(mtime)
                medizy_backup_success_status.set(is_fresh)
                return

        medizy_backup_success_status.set(0.0)
    except Exception as e:
        logger.debug(f"Erreur mise à jour métrique backup: {e}")


# ==============================================================================
# 3. CONFIGURATION INSTRUMENTATOR PROMETHEUS
# ==============================================================================

def setup_prometheus_instrumentator(app):
    """
    Configure et attache l'instrumentateur Prometheus FastAPI avec exposition sur `/metrics`.
    """
    from starlette.requests import Request

    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
        inprogress_name="medizy_http_requests_inprogress",
        inprogress_labels=True,
    )

    # Middleware mettant à jour les métriques dynamiques à chaque scrape
    @app.middleware("http")
    async def metrics_scrape_updater_middleware(request: Request, call_next):
        if request.url.path == "/metrics":
            update_pending_suggestions_gauge()
            update_backup_freshness_gauge()
        return await call_next(request)

    # Enregistrement de l'instrumentateur sur l'application FastAPI
    instrumentator.instrument(app).expose(app, endpoint="/metrics", tags=["Surveillance"])

    logger.info("Point d'accès Prometheus '/metrics' configuré avec succès.")
    return instrumentator
