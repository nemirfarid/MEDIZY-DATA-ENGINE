# MEDIZY — Guide Production : Observabilité Prometheus, Synchronisation NIBRAS & Sauvegarde PostGIS

Ce guide d'exploitation présente les briques de surveillance applicative, la passerelle d'exportation continue pour l'agent conversationnel **NIBRAS** et la politique de sauvegarde & reprise après sinistre (Disaster Recovery) de la base de données spatiale PostGIS.

---

## 1. Métriques & Observabilité (Prometheus / Grafana)

### A. Point d'accès `/metrics`
L'API FastAPI expose un point d'accès standardisé au format texte Prometheus via [`medizy_pipeline/api/metrics.py`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/api/metrics.py) :
```http
GET /metrics
```

### B. Indicateurs Clés Trackés
| Nom de la Métrique | Type | Labels | Description & Requête PromQL |
| :--- | :--- | :--- | :--- |
| `medizy_geosearch_duration_seconds` | `Histogram` | `endpoint`, `type_filter`, `wilaya` | **Latence p95/p99 des requêtes géospatiales** :<br>`histogram_quantile(0.95, sum(rate(medizy_geosearch_duration_seconds_bucket[5m])) by (le, endpoint))` |
| `medizy_geosearch_requests_total` | `Counter` | `endpoint`, `status` | **Débit de requêtes géospatiales (RPS)** :<br>`sum(rate(medizy_geosearch_requests_total[1m])) by (endpoint)` |
| `pending_suggestions_gauge` | `Gauge` | — | **Volume de contributions en attente de modération** (dynamiquement actualisée lors de chaque scrape Prometheus). |
| `osm_mirror_failover_total` | `Counter` | `wilaya`, `target_mirror` | **Compteur d'incidents de bascule de miroirs OSM Overpass** lors des cycles nocturnes. |
| `medizy_nibras_sync_exports_total` | `Counter` | `status` | **Volume d'extractions sémantiques pour NIBRAS**. |

### C. Déploiement de la Pile de Surveillance
- **Configuration Prometheus** : [`prometheus.yml`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/observability/prometheus.yml)
- **Dashboard Grafana Provisionné** : [`grafana_dashboard.json`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/observability/grafana_dashboard.json)
- Les services `prometheus` (port `9090`) et `grafana` (port `3000`) sont intégrés directement dans [`docker-compose.yml`](file:///c:/SANTE_DZ_SCRAPER/docker-compose.yml).

```bash
# Démarrer l'ensemble de la pile avec observabilité
docker-compose up -d prometheus grafana
```
Accès Grafana : `http://localhost:3000` (identifiant: `admin`, mot de passe: `MedizyGrafana2026!`).

---

## 2. Passerelle de Synchronisation Externe (Export API pour NIBRAS)

Pour permettre à l'agent conversationnel **NIBRAS** de maintenir son index vectoriel local à jour sans charger la base relationnelle PostGIS de requêtes analytiques lourdes, un endpoint dédié est disponible :

### Endpoint :
```http
GET /api/v1/facilities/export/latest?cursor=100&limit=50&updated_since=2026-10-01T00:00:00Z
```

### Paramètres de Requête :
- **`cursor`** : Entier optionnel. Curseur strictly monotone basé sur l'identifiant séquentiel (`id > cursor`). Élimine les décalages de pagination par offset.
- **`limit`** : Entier (défaut : 100, maximum : 500). Taille du lot de données retourné.
- **`updated_since`** : Chaîne ISO-8601 optionnelle (ex: `2026-10-28T00:00:00Z`). Ne sélectionne que les fiches créées ou modifiées après cette date.
- **`wilaya`** : Chaîne optionnelle (ex: `Alger` ou `16`) pour une indexation ciblée.

### Exemple de Réponse Structurée JSON :
```json
{
  "count": 3,
  "has_more": true,
  "next_cursor": "3",
  "sync_timestamp": "2026-10-28T02:48:00Z",
  "facilities": [
    {
      "id": 1,
      "name": "Bordj Kiffan",
      "type": "Clinique",
      "wilaya": "Alger",
      "wilaya_code": "16",
      "commune": "Bordj El Kiffan",
      "address": "Rue Principale",
      "phone": "021 20 00 00",
      "latitude": 36.74671,
      "longitude": 3.19058,
      "is_claimed": false,
      "is_verified": true,
      "source": "osm",
      "created_at": "2026-10-28 00:37:00",
      "updated_at": "2026-10-28 00:37:00",
      "embedding_context": "Clinique 'Bordj Kiffan' à Bordj El Kiffan, Wilaya de Alger. Adresse : Rue Principale. Téléphone : 021 20 00 00. Statut : Établissement vérifié et certifié."
    }
  ]
}
```

> **Note d'intégration NIBRAS** : Le champ `embedding_context` fournit un texte synthétique pré-nettoyé, immédiatement prêt à être vectorisé (via modèle d'embedding bilingue arabe/français) pour alimenter la base de connaissances RAG de l'agent NIBRAS.

---

## 3. Plan de Sauvegarde Automatisé PostGIS (Backup & Disaster Recovery)

### A. Scripts Opérationnels
- Script POSIX Linux / Conteneurs : [`scripts/backup_postgis.sh`](file:///c:/SANTE_DZ_SCRAPER/scripts/backup_postgis.sh)
- Script PowerShell Windows : [`scripts/backup_postgis.ps1`](file:///c:/SANTE_DZ_SCRAPER/scripts/backup_postgis.ps1)

### B. Caractéristiques du Processus de Sauvegarde
1. **Extraction Binaire Compressée** : Utilisation de `pg_dump -Fc -Z 9` (format custom PostGIS compressé avec détection des objets spatiaux et blobs).
2. **Vérification d'Intégrité DR** : Exécution immédiate de `pg_restore --list "$BACKUP_PATH"` pour valider que le fichier n'est ni tronqué ni corrompu. En cas d'anomalie, une alerte est levée et le script se termine avec le code d'erreur `2`.
3. **Rotation Glissante sur 14 Jours** : Les archives locales antérieures à 14 jours sont automatiquement purgées par commande `find -mtime +14`.
4. **Transfert Déporté Sécurisé (S3)** : Si la variable `S3_BUCKET` est renseignée, l'archive est transférée sur AWS S3 / MinIO avec la classe de stockage `STANDARD_IA`.
5. **Notification Webhook** : Synthèse transmise sur Slack / Teams / Discord en cas de succès ou d'échec critique.

### C. Automatisation Cron (Serveur de Production Linux)
Dans `/etc/cron.d/medizy-backup` :
```cron
# Sauvegarde quotidienne à 03h00 (après le cycle d'ingestion de 02h00)
0 3 * * * root POSTGRES_HOST=localhost POSTGRES_DB=medizy_db S3_BUCKET=s3://medizy-backups-dz/postgis/ /opt/medizy/scripts/backup_postgis.sh >> /var/log/medizy_backup.log 2>&1
```

### D. Procédure de Restauration d'Urgence (Disaster Recovery Runbook)
En cas de sinistre ou de restauration sur un nouvel environnement :
```bash
# 1. Recréer la base vide avec les extensions spatiales
psql -U medizy_user -d postgres -c "DROP DATABASE IF EXISTS medizy_db; CREATE DATABASE medizy_db;"
psql -U medizy_user -d medizy_db -c "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS unaccent; CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# 2. Restaurer l'archive la plus récente en mode multi-jobs (-j 4)
pg_restore -h localhost -p 5432 -U medizy_user -d medizy_db -j 4 -v /var/backups/medizy/medizy_postgis_medizy_db_20261028_030000.dump

# 3. Vérifier le volume des données restaurées
psql -U medizy_user -d medizy_db -c "SELECT COUNT(*) FROM facilities;"
```
