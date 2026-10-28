# MEDIZY — Runbook d'Exploitation de Production & Plan de Reprise d'Activité (PRA / DRP)

Ce document constitue le référentiel opérationnel officiel de l'équipe d'astreinte et d'ingénierie DevOps pour la plateforme nationale de santé **MEDIZY**.

---

## 1. Runbook d'Exploitation Quotidienne

### A. Supervision & Santé des Conteneurs (Docker Compose)
Le cluster MEDIZY orchestre 6 services conteneurisés interconnectés sur le réseau interne :
- `medizy-postgis` : Base de données spatiale PostgreSQL 16 + PostGIS 3.4
- `medizy-redis` : Cache et limitation de débit anti-brute-force
- `medizy-api` : Microservice FastAPI, documentation Swagger et métriques
- `medizy-scheduler` : Planificateur autonome d'ingestion nocturne (02h00)
- `medizy-prometheus` : Moteur de collecte et stockage des métriques TSDB
- `medizy-grafana` : Tableaux de bord de surveillance visuelle

#### 1. Inspection de l'état des services et des sondes de santé :
```bash
# Vérification globale du statut et de l'état 'healthy'
docker compose ps

# Exemple de retour nominal :
# NAME                IMAGE                    STATUS                   PORTS
# medizy-postgis      postgis/postgis:16-3.4   Up (healthy)             0.0.0.0:5432->5432/tcp
# medizy-redis        redis:7-alpine           Up (healthy)             0.0.0.0:6379->6379/tcp
# medizy-api          medizy-api:latest        Up                       0.0.0.0:8000->8000/tcp
# medizy-scheduler    medizy-api:latest        Up                       
# medizy-prometheus   prom/prometheus:v2.51.0  Up                       0.0.0.0:9090->9090/tcp
# medizy-grafana      grafana/grafana:10.4.0   Up                       0.0.0.0:3000->3000/tcp
```

#### 2. Consultation des journaux d'exécution en temps réel :
```bash
# Suivre l'activité de l'API et les requêtes entrantes
docker compose logs -f --tail=100 api

# Suivre les cycles d'ingestion nocturne et bascules de miroirs
docker compose logs -f --tail=100 ingest-scheduler

# Suivre les métriques collectées par Prometheus
docker compose logs -f --tail=50 prometheus
```

---

### B. Procédures d'Astreinte en Cas d'Alerte

#### ALERTE 1 : Accumulation de Suggestions (`pending_suggestions_gauge > 50`)
- **Déclencheur** : La jauge Prometheus `pending_suggestions_gauge` dépasse le seuil critique de 50 contributions non traitées.
- **Impact** : Risque de retard d'actualisation des nouveaux établissements et engorgement de la file d'attente.
- **Arbre d'Intervention Pas à Pas** :
  1. Se connecter sur le dashboard d'administration MEDIZY : `https://admin.medizy.dz` (ou `http://localhost:8000/admin`).
  2. Activer le filtre **« Doublons potentiels uniquement »** pour isoler les suggestions à moins de 100 m des structures certifiées existantes.
  3. Utiliser le composant miniature [`DuplicateComparisonMap.tsx`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/frontend/DuplicateComparisonMap.tsx) pour statuer rapidement :
     - *Si doublon avéré* : Cliquer sur **« Rejeter comme Doublon »** (motif horodaté consigné).
     - *Si extension ou nouvelle clinique* : Cliquer sur **« Valider la Structure »**.
  4. Si l'afflux est massif et frauduleux (spam/bot) :
     - Vérifier l'adresse IP source dans les logs : `docker compose logs api | grep "/facilities/suggest"`.
     - Appliquer un blocage immédiat au niveau du reverse proxy ou réduire la fenêtre du rate-limiter Redis.

---

#### ALERTE 2 : Incidents Multiples de Miroirs OSM (`osm_mirror_failover_total > 3`)
- **Déclencheur** : Plus de 3 basculements consécutifs de miroirs OpenStreetMap Overpass lors d'un cycle nocturne.
- **Impact** : Dégradation du débit d'ingestion ou blocage temporaire par rate-limiting tiers (HTTP 429/504).
- **Arbre d'Intervention Pas à Pas** :
  1. Inspecter le journal structuré d'ingestion :
     ```bash
     tail -n 50 medizy_ingest_audit.jsonl | grep "FAILOVER"
     ```
  2. Vérifier la disponibilité publique des miroirs configurés :
     - `https://overpass-api.de/api/status`
     - `https://lz4.overpass-api.de/api/status`
     - `https://overpass.kumi.systems/api/status`
     - `https://overpass.private.coffee/api/status`
  3. Si les serveurs mondiaux sont sous quota ou bloqués par IP :
     - Augmenter temporairement la temporisation inter-wilayas (`INGEST_DELAY_SECONDS=5.0` ou `7.0`).
     - Relancer manuellement le cycle sur les wilayas échouées uniquement :
       ```bash
       python -m medizy_pipeline.scheduler.cron_ingest --now --wilayas 16 31 27 --delay 5.0
       ```

#### ALERTE 3 : Sauvegarde Périmée ou Corrompue (`medizy_backup_success_status == 0`)
- **Déclencheur** : La jauge Prometheus `medizy_backup_success_status` tombe à 0 ou aucune sauvegarde valide n'a été certifiée depuis plus de 26 heures.
- **Impact** : Rupture du contrat RPO (< 24h) et risque de perte de données en cas de sinistre.
- **Arbre d'Intervention Pas à Pas** :
  1. Exécuter manuellement la sonde de diagnostic :
     ```bash
     ./scripts/check_backup_freshness.sh
     ```
  2. Si l'archive du jour est absente :
     - Vérifier l'espace disque résiduel : `df -h /var/backups/medizy` ou `docker compose exec postgis df -h`.
     - Lancer immédiatement une sauvegarde manuelle certifiée :
       ```bash
       ./scripts/backup_postgis.sh
       ```
  3. Si l'archive a échoué au contrôle `pg_restore --list` :
     - Vérifier les logs PostgreSQL pour identifier les tables verrouillées ou transactions bloquantes.
     - Relancer une sauvegarde complète hors ligne après bascule temporaire en lecture seule.

---

### C. Procédure de Bascule en Mode Maintenance / Lecture Seule (Read-Only Mode)

Lors d'opérations lourdes d'infrastructure (migration de schéma, réindexation spatiale globale, maintenance matérielle, ou avant restauration DRP), l'API peut être basculée instantanément en **mode lecture seule**.
Dans ce mode, la consultation du public (recherche, géolocalisation, export NIBRAS) reste **100% active**, mais toutes les requêtes en écriture (`POST /facilities/suggest`, actions de modération) sont interceptées avec un code `HTTP 503 Service Unavailable`.

#### 1. Activer le mode lecture seule :
```bash
# Option A : Reconfiguration à chaud sans interruption de service
docker compose exec api sh -c "export READ_ONLY_MODE=true"

# Option B : Persistance via docker-compose (recommandé pour les maintenances planifiées)
READ_ONLY_MODE=true docker compose up -d api
```

#### 2. Vérifier l'activation du mode :
```bash
# Vérification via la sonde de santé (doit retourner "mode": "read_only")
curl -s http://localhost:8000/health | jq .mode
# "read_only"

# Test de rejet d'une écriture
curl -i -X POST http://localhost:8000/api/v1/facilities/suggest -H "Content-Type: application/json" -d '{}'
# HTTP/1.1 503 Service Unavailable
# {"error":"READ_ONLY_MODE","status":"maintenance","message":"La plateforme MEDIZY est temporairement en mode lecture seule..."}
```

#### 3. Désactiver le mode et rétablir les écritures :
```bash
READ_ONLY_MODE=false docker compose up -d api
curl -s http://localhost:8000/health | jq .mode
# "read_write"
```

---

## 2. Procédure Détaillée de Reprise après Sinistre (Disaster Recovery Plan)


Ce protocole s'applique en cas de perte totale de conteneur, de corruption matérielle ou de migration d'urgence vers un nouveau serveur d'hébergement.

### RPO & RTO Cibles :
- **RPO (Perte Maximale Admissible)** : 24 heures (sauvegarde quotidienne à 03h00).
- **RTO (Temps de Reprise Admissible)** : < 15 minutes.

### Protocole Opérationnel Pas à Pas :

```
                ┌───────────────────────────────────────┐
                │ 1. Gel des écritures (API Stop)       │
                └──────────────────┬────────────────────┘
                                   │
                ┌──────────────────▼────────────────────┐
                │ 2. Récupération de l'archive .dump    │
                └──────────────────┬────────────────────┘
                                   │
                ┌──────────────────▼────────────────────┐
                │ 3. Recréation Base & Extensions PostGIS│
                └──────────────────┬────────────────────┘
                                   │
                ┌──────────────────▼────────────────────┐
                │ 4. Restauration multi-jobs pg_restore │
                └──────────────────┬────────────────────┘
                                   │
                ┌──────────────────▼────────────────────┐
                │ 5. Réindexation GiST & VACUUM ANALYZE │
                └──────────────────┬────────────────────┘
                                   │
                ┌──────────────────▼────────────────────┐
                │ 6. Contrôle intégrité & Réouverture   │
                └───────────────────────────────────────┘
```

#### Étape 1 : Geler le trafic et isoler l'instance
```bash
# Stopper immédiatement l'API et le planificateur pour éviter toute écriture concurrente
docker compose stop api ingest-scheduler
```

#### Étape 2 : Récupérer la sauvegarde certifiée la plus récente
```bash
# Télécharger depuis le stockage S3 distant si le stockage local est indisponible
aws s3 cp s3://medizy-backups-dz/postgis/medizy_postgis_medizy_db_LATEST.dump /var/backups/medizy/
```

#### Étape 3 : Exécuter le script automatisé de reprise après sinistre
Le script dédié [`scripts/restore_postgis.sh`](file:///c:/SANTE_DZ_SCRAPER/scripts/restore_postgis.sh) automatise l'ensemble de la séquence :
```bash
chmod +x scripts/restore_postgis.sh
./scripts/restore_postgis.sh /var/backups/medizy/medizy_postgis_medizy_db_LATEST.dump
```

*Détail des opérations exécutées sous le capot par le script :*
1. **Terminaison des sessions actives** :
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'medizy_db' AND pid <> pg_backend_pid();
   DROP DATABASE IF EXISTS medizy_db;
   CREATE DATABASE medizy_db OWNER medizy_user ENCODING 'UTF8';
   ```
2. **Initialisation des extensions spatiales indispensables** :
   ```sql
   \c medizy_db
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS unaccent;
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   ```
3. **Restauration parallèle haute performance** :
   ```bash
   pg_restore -h localhost -p 5432 -U medizy_user -d medizy_db --clean --if-exists --no-owner --jobs=4 -v /chemin/sauvegarde.dump
   ```
4. **Réindexation concurrente et mise à jour des statistiques géospatiales** :
   ```sql
   REINDEX TABLE CONCURRENTLY facilities;
   VACUUM ANALYZE facilities;
   VACUUM ANALYZE facility_suggestions;
   ```

#### Étape 4 : Sanity Check & Validation Géographique
Vérifier que les données et les coordonnées géographiques sont intactes :
```sql
-- Nombre total d'établissements restaurés (doit être >= 1 650)
SELECT COUNT(*) FROM facilities;

-- Bounding box nationale (doit couvrir le territoire algérien : ~18.9°N à ~37.1°N, -8.6°O à 11.9°E)
SELECT ST_AsText(ST_Extent(geom)) FROM facilities;

-- Vérification de l'utilisation de l'index GiST
EXPLAIN ANALYZE
SELECT id, name FROM facilities
WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(3.05, 36.75), 4326)::geography, 5000);
```

#### Étape 5 : Réouverture du trafic de production
```bash
docker compose start api ingest-scheduler
curl -I http://localhost:8000/health
```

---

## 3. Protocole de Livraison & Mise en Service

### A. Matrice des Variables d'Environnement de Production ([`.env.example`](file:///c:/SANTE_DZ_SCRAPER/.env.example))

| Variable | Exemple de Valeur en Production | Obligatoire ? | Rôle & Périmètre de Sécurité |
| :--- | :--- | :---: | :--- |
| `DATABASE_URL` | `postgresql://medizy_user:SECRET@postgis:5432/medizy_db` | **OUI** | Chaîne de connexion PostGIS du pool de threads applicatif. |
| `ADMIN_JWT_SECRET` | `c84a7e91d3f...64_caracteres_aleatoires` | **OUI** | Clé cryptographique symétrique HS256 pour la signature des jetons admin (24h). |
| `ADMIN_API_KEY` | `medizy-admin-supersecret-token-2026` | **OUI** | En-tête de secours `X-Admin-Api-Key` pour les scripts d'administration système. |
| `REDIS_URL` | `redis://redis:6379/0` | **OUI** | Stockage en mémoire vive du rate-limiting (anti-brute-force). |
| `S3_BUCKET` | `s3://medizy-backups-production/postgis/` | **OUI** | Cible déportée pour le transfert quotidien des archives compressées. |
| `INGEST_SCHEDULE_TIME` | `02:00` | Non (Défaut) | Heure locale de déclenchement du pipeline d'enrichissement. |
| `ENABLE_METRICS` | `true` | Non (Défaut) | Active l'instrumentation et le point d'accès `/metrics`. |
| `CORS_ORIGINS` | `https://medizy.dz,https://admin.medizy.dz` | **OUI** | Domaines autorisés à interroger l'API publique et le back-office. |

---

### B. Commande Unique de Déploiement à Froid (Cold Start)

Depuis la racine du projet, exécutez la commande d'orchestration unifiée :

```bash
docker compose --env-file .env.production up -d --build
```

---

### C. Checklist de Validation en 5 Points (Go-Live Gate)

Avant d'ouvrir le trafic DNS au grand public et à l'application mobile, l'ingénieur de garde **DOIT** cocher l'ensemble des 5 critères suivants :

```
[ ] POINT 1 : Sonde de Santé Système (Healthcheck)
    Commande : curl -s http://localhost:8000/health | grep '"status":"healthy"'
    Critère  : Réponse HTTP 200 avec "database_backend":"PostgreSQL/PostGIS".

[ ] POINT 2 : Intégrité Cartographique & Recherche Spatiale
    Commande : curl -s "http://localhost:8000/api/v1/facilities/nearby?lat=36.75&lon=3.05&radius_km=5"
    Critère  : Retourne les structures de santé d'Alger triées par distance_meters croissante avec badges.

[ ] POINT 3 : Synchronisation NIBRAS (Passerelle Sémantique)
    Commande : curl -s "http://localhost:8000/api/v1/facilities/export/latest?limit=1"
    Critère  : Présence des champs 'sync_timestamp' et 'embedding_context' non nuls.

[ ] POINT 4 : Protection Anti-Brute-Force & Observabilité
    Commande : curl -s http://localhost:8000/metrics | grep "pending_suggestions_gauge"
    Critère  : Flux Prometheus actif et compteur de rate-limiting opérationnel sur Redis.

[ ] POINT 5 : Validation de la Sauvegarde Initiale Certifiée
    Commande : ./scripts/backup_postgis.sh
    Critère  : Archive générée dans /var/backups/medizy/ avec statut 'Contrôle d'intégrité VALIDÉ'.
```
