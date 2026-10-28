#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Planificateur et Orchestrateur des Mises à Jour Périodiques
=============================================================================
Ce module gère l'exécution automatisée (ex: chaque nuit à 02h00) du pipeline
d'ingestion des établissements de santé à travers les 58 wilayas d'Algérie.

Fonctionnalités clés :
- Exécution non disruptive (throttling, délai inter-wilayas configurable).
- Résilience et bascule automatique sur les miroirs OpenStreetMap Overpass.
- Journalisation structurée en format JSON (Structured JSON Logging).
- Mode démon autonome (boucle temporelle intelligente) ou mode one-shot (Cron).
- Gestion propre des signaux d'arrêt système (SIGTERM, SIGINT).
"""

import argparse
import datetime
import json
import logging
import os
import signal
import sys
import time
import urllib.request
from typing import Dict, List, Optional

from medizy_pipeline.enrichment.ingest_pipeline import (
    ALGERIAN_WILAYAS,
    FacilityDataStore,
    HealthEnrichmentPipeline,
    IngestionReport,
)
from medizy_pipeline.enrichment.osm_overpass import OVERPASS_ENDPOINTS

# Configuration du logger structuré
logger = logging.getLogger("medizy.scheduler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
    logger.addHandler(handler)


class StructuredAuditLogger:
    """Gestionnaire de logs structurés au format JSON pour audits et dashboards DevOps."""

    def __init__(self, log_path: str = "medizy_ingest_structured.log"):
        self.log_path = log_path

    def log_event(self, event_type: str, payload: dict):
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": event_type,
            **payload,
        }
        json_line = json.dumps(entry, ensure_ascii=False)
        logger.info(f"AUDIT_EVENT [{event_type}]: {json_line}")
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json_line + "\n")
        except Exception as e:
            logger.warning(f"Impossible d'écrire dans le fichier d'audit {self.log_path}: {e}")


class IngestScheduler:
    """Orchestrateur périodique d'ingestion avec résilience et limitation de débit."""

    def __init__(
        self,
        schedule_time: str = "02:00",
        delay_seconds: float = 3.0,
        all_wilayas: bool = True,
        target_wilayas: Optional[List[str]] = None,
        use_google: bool = False,
        db_url: Optional[str] = None,
        dry_run: bool = False,
        audit_file: str = "medizy_ingest_audit.jsonl",
        webhook_url: Optional[str] = None,
    ):
        self.schedule_time = schedule_time
        self.delay_seconds = delay_seconds
        self.all_wilayas = all_wilayas
        self.target_wilayas = target_wilayas or (["16", "31", "27"] if not all_wilayas else [])
        self.use_google = use_google
        self.db_url = db_url or os.environ.get("DATABASE_URL")
        self.dry_run = dry_run
        self.audit = StructuredAuditLogger(audit_file)
        self.webhook_url = webhook_url or os.environ.get("INGEST_ALERT_WEBHOOK_URL")
        self._is_running = True

        # Enregistrement des gestionnaires de signaux
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame):
        logger.warning(f"Signal reçu ({signum}). Arrêt gracieux du planificateur...")
        self._is_running = False

    def calculate_seconds_until_next_run(self) -> float:
        """Calcule le délai exact en secondes jusqu'à la prochaine occurrence (ex: 02h00)."""
        now = datetime.datetime.now()
        target_hour, target_minute = map(int, self.schedule_time.split(":"))
        target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        return (target - now).total_seconds()

    def run_cycle(self) -> dict:
        """Exécute un cycle complet d'ingestion avec résilience et rapport."""
        run_id = f"ingest_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        start_ts = time.time()

        self.audit.log_event(
            "INGEST_CYCLE_STARTED",
            {
                "run_id": run_id,
                "all_wilayas": self.all_wilayas,
                "target_wilayas": self.target_wilayas,
                "delay_seconds": self.delay_seconds,
                "dry_run": self.dry_run,
                "mirrors_available": len(OVERPASS_ENDPOINTS),
            },
        )

        datastore = FacilityDataStore(db_url=self.db_url)
        pipeline = HealthEnrichmentPipeline(
            datastore=datastore,
            google_api_key=os.environ.get("GOOGLE_PLACES_API_KEY") if self.use_google else None,
        )

        # Détermination des wilayas à traiter
        if self.all_wilayas:
            selected_objs = list(ALGERIAN_WILAYAS)
        else:
            selected_objs = [
                w for w in ALGERIAN_WILAYAS
                if w["code"] in self.target_wilayas or w["name"].lower() in [tw.lower() for tw in self.target_wilayas]
            ]

        report = IngestionReport()
        mirror_switches = 0
        current_endpoint = pipeline.osm_client.endpoint

        for w_obj in selected_objs:
            if not self._is_running:
                logger.warning("Interruption demandée. Arrêt du cycle d'ingestion.")
                break

            w_code = w_obj["code"]
            w_name = w_obj["name"]

            try:
                # Vérifier si un basculement de miroir a eu lieu
                before_endpoint = pipeline.osm_client.endpoint
                if self.dry_run:
                    candidates = pipeline.osm_client.fetch_wilaya_facilities(
                        wilaya_name=w_name, bbox=w_obj.get("bbox")
                    )
                    stats = {
                        "fetched": len(candidates),
                        "inserted": len(candidates),
                        "duplicates": 0,
                        "errors": 0,
                    }
                else:
                    stats = pipeline.run_for_wilaya(w_obj, use_google=self.use_google)

                after_endpoint = pipeline.osm_client.endpoint
                if before_endpoint != after_endpoint:
                    mirror_switches += 1
                    self.audit.log_event(
                        "MIRROR_FAILOVER_TRIGGERED",
                        {
                            "run_id": run_id,
                            "previous_endpoint": before_endpoint,
                            "new_endpoint": after_endpoint,
                            "wilaya": w_name,
                        },
                    )

                report.wilaya_stats[w_name] = stats
                report.total_fetched += stats["fetched"]
                report.total_new_inserted += stats["inserted"]
                report.total_duplicates_skipped += stats["duplicates"]
                report.total_errors += stats["errors"]

                logger.info(
                    f"[{w_code} - {w_name}] Collectés: {stats['fetched']} | "
                    f"Nouveaux: {stats['inserted']} | Doublons: {stats['duplicates']} | Erreurs: {stats['errors']}"
                )

                # Pause non bloquante entre wilayas pour ne pas saturer l'instance de prod et l'API Overpass
                time.sleep(self.delay_seconds)

            except Exception as e:
                report.total_errors += 1
                logger.error(f"Échec sur la wilaya {w_name} ({w_code}): {e}")
                self.audit.log_event(
                    "WILAYA_PROCESSING_ERROR",
                    {"run_id": run_id, "wilaya": w_name, "error": str(e)},
                )

        duration = round(time.time() - start_ts, 2)
        summary = {
            "run_id": run_id,
            "status": "COMPLETED" if self._is_running else "ABORTED",
            "duration_seconds": duration,
            "wilayas_processed": len(report.wilaya_stats),
            "total_fetched": report.total_fetched,
            "total_new_inserted": report.total_new_inserted,
            "total_duplicates_skipped": report.total_duplicates_skipped,
            "total_errors": report.total_errors,
            "mirror_switches": mirror_switches,
            "active_endpoint": pipeline.osm_client.endpoint,
        }

        self.audit.log_event("INGEST_CYCLE_FINISHED", summary)

        # Envoi d'une notification webhook si configurée
        if self.webhook_url:
            self._notify_webhook(summary)

        return summary

    def _notify_webhook(self, summary: dict):
        """Envoie un résumé d'exécution au webhook de surveillance (ex: Slack / Teams)."""
        try:
            payload = {
                "text": (
                    f"🏥 *MEDIZY Ingestion Report [{summary['status']}]*\n"
                    f"• *ID Run* : `{summary['run_id']}`\n"
                    f"• *Durée* : {summary['duration_seconds']}s\n"
                    f"• *Wilayas traitées* : {summary['wilayas_processed']}/58\n"
                    f"• *Nouveaux établissements* : *+{summary['total_new_inserted']}*\n"
                    f"• *Doublons ignorés* : {summary['total_duplicates_skipped']}\n"
                    f"• *Erreurs* : {summary['total_errors']}\n"
                    f"• *Basculements miroirs OSM* : {summary['mirror_switches']}"
                )
            }
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                logger.info(f"Notification webhook transmise avec statut {resp.status}")
        except Exception as e:
            logger.warning(f"Impossible d'envoyer la notification webhook: {e}")

    def start_daemon(self):
        """Lance la boucle de planification infinie (exécutée chaque nuit à l'heure programmée)."""
        logger.info(
            f"Démarrage du démon planificateur MEDIZY. Prochaine exécution programmée à {self.schedule_time}."
        )
        while self._is_running:
            delay = self.calculate_seconds_until_next_run()
            next_run_dt = datetime.datetime.now() + datetime.timedelta(seconds=delay)
            logger.info(
                f"En veille... Prochain cycle prévu le {next_run_dt.strftime('%Y-%m-%d à %H:%M:%S')} (dans {delay / 3600:.2f} heures)."
            )

            # Sommeil par tranches de 10s pour réagir immédiatement aux signaux d'arrêt
            sleep_elapsed = 0
            while sleep_elapsed < delay and self._is_running:
                step = min(10.0, delay - sleep_elapsed)
                time.sleep(step)
                sleep_elapsed += step

            if self._is_running:
                logger.info("Déclenchement de l'ingestion programmée nocturne.")
                self.run_cycle()


def run_nightly_job(
    all_wilayas: bool = True,
    delay: float = 3.0,
    db_url: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Point d'entrée direct pour scripts Cron ou Workers Celery."""
    scheduler = IngestScheduler(
        delay_seconds=delay,
        all_wilayas=all_wilayas,
        db_url=db_url,
        dry_run=dry_run,
    )
    return scheduler.run_cycle()


def main():
    parser = argparse.ArgumentParser(
        description="Planificateur et orchestrateur d'ingestion nocturne MEDIZY",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Démarrer en mode démon résidentiel (veille jusqu'à l'heure programmée chaque jour)",
    )
    parser.add_argument(
        "--time",
        type=str,
        default="02:00",
        help="Heure de déclenchement nocturne en mode démon (format HH:MM, défaut: 02:00)",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Exécuter un cycle d'ingestion immédiatement et quitter",
    )
    parser.add_argument(
        "--wilayas",
        nargs="*",
        help="Codes ou noms des wilayas à traiter (ex: --wilayas 16 31 27)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="Traiter les 58 wilayas d'Algérie (activé par défaut)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Délai en secondes entre deux requêtes Overpass (défaut: 3.0s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simuler l'ingestion sans altérer la base de production",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        help="Chaîne de connexion de la base de données cible",
    )
    parser.add_argument(
        "--audit-file",
        type=str,
        default="medizy_ingest_audit.jsonl",
        help="Fichier de journalisation d'audit structuré (défaut: medizy_ingest_audit.jsonl)",
    )

    args = parser.parse_args()

    scheduler = IngestScheduler(
        schedule_time=args.time,
        delay_seconds=args.delay,
        all_wilayas=not bool(args.wilayas),
        target_wilayas=args.wilayas,
        db_url=args.db_url,
        dry_run=args.dry_run,
        audit_file=args.audit_file,
    )

    if args.now:
        logger.info("Exécution immédiate (--now demandée).")
        result = scheduler.run_cycle()
        print(f"\nRésultat du cycle : {json.dumps(result, indent=2, ensure_ascii=False)}")
    elif args.daemon:
        scheduler.start_daemon()
    else:
        # Si aucun argument, afficher l'aide ou exécuter un cycle test
        parser.print_help()


if __name__ == "__main__":
    main()
