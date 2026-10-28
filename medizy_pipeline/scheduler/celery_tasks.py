"""
MEDIZY / SANTÉ DZ — Tâches Planifiées Celery & APScheduler (Optionnel)
====================================================================
Ce module fournit l'intégration prête à l'emploi avec Celery Beat
et APScheduler pour les environnements de production Kubernetes ou Docker Swarm.

Configuration Celery Beat type (ex: celerybeat-schedule) :
    CELERY_BEAT_SCHEDULE = {
        'nightly-health-facilities-ingest': {
            'task': 'medizy_pipeline.scheduler.celery_tasks.task_nightly_health_ingest',
            'schedule': crontab(hour=2, minute=0),
            'kwargs': {'all_wilayas': True, 'delay_seconds': 3.0},
        },
    }
"""

import logging
import os

logger = logging.getLogger("medizy.celery_tasks")

try:
    from celery import Celery
    from celery.schedules import crontab

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    celery_app = Celery("medizy_scheduler", broker=REDIS_URL, backend=REDIS_URL)

    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Africa/Algiers",
        enable_utc=True,
    )

    @celery_app.task(name="medizy_pipeline.scheduler.celery_tasks.task_nightly_health_ingest", bind=True, max_retries=3)
    def task_nightly_health_ingest(self, all_wilayas: bool = True, delay_seconds: float = 3.0, dry_run: bool = False):
        """Tâche Celery nocturne exécutant l'ingestion sans bloquer les workers synchrones."""
        from medizy_pipeline.scheduler.cron_ingest import IngestScheduler

        logger.info("Démarrage de la tâche Celery nocturne d'ingestion des établissements de santé...")
        try:
            scheduler = IngestScheduler(
                delay_seconds=delay_seconds,
                all_wilayas=all_wilayas,
                dry_run=dry_run,
            )
            return scheduler.run_cycle()
        except Exception as exc:
            logger.error(f"Échec tâche Celery: {exc}. Nouvelle tentative programmée...")
            raise self.retry(exc=exc, countdown=300)

except ImportError:
    celery_app = None  # Celery n'est pas installé dans l'environnement local


def configure_apscheduler(scheduler_instance, schedule_time: str = "02:00"):
    """Permet de brancher la tâche nocturne sur une instance APScheduler existante."""
    from medizy_pipeline.scheduler.cron_ingest import run_nightly_job

    hour, minute = map(int, schedule_time.split(":"))
    scheduler_instance.add_job(
        run_nightly_job,
        trigger="cron",
        hour=hour,
        minute=minute,
        id="medizy_nightly_ingest",
        name="Ingestion Nocturne Médicale MEDIZY",
        replace_existing=True,
    )
    logger.info(f"Tâche APScheduler enregistrée avec succès pour chaque nuit à {schedule_time}.")
