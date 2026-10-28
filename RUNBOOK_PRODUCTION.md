# MEDIZY — Runbook d'Exploitation & Plan de Reprise d'Activité (PRA / DRP)

Le guide d'exploitation de référence pour la production est documenté en détail dans :
👉 [`medizy_pipeline/RUNBOOK_PRODUCTION_ET_DISASTER_RECOVERY.md`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/RUNBOOK_PRODUCTION_ET_DISASTER_RECOVERY.md)

### Résumé des commandes essentielles :

```bash
# 1. Démarrer toute l'infrastructure (PostGIS, Redis, API, Scheduler, Prometheus, Grafana)
docker compose up -d

# 2. Vérifier la santé des services
docker compose ps

# 3. Lancer une sauvegarde manuelle certifiée
./scripts/backup_postgis.sh

# 4. Restaurer une sauvegarde en urgence (Disaster Recovery)
./scripts/restore_postgis.sh /chemin/vers/sauvegarde.dump

# 5. Consulter les métriques Prometheus
curl http://localhost:8000/metrics
```
