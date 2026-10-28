# MEDIZY — Guide d'Industrialisation, Déploiement PostGIS & Modération Administrative

Ce document détaille la procédure complète pour basculer le système de données de santé MEDIZY de l'environnement de développement vers la production PostGIS conteneurisée, ainsi que l'exploitation du back-office de modération des suggestions citoyennes.

---

## 1. Déploiement de l'Infrastructure PostGIS (Docker Compose)

### A. Démarrage du cluster PostGIS
Le fichier `docker-compose.yml` provisionne une instance PostgreSQL 16 avec PostGIS 3.4, intégrant les extensions spatiales et le schéma DDL initialisé via le point de montage `/docker-entrypoint-initdb.d/001_init.sql`.

```bash
# Démarrer le conteneur PostGIS en tâche de fond
docker-compose up -d postgis

# Vérifier la disponibilité et le statut de santé
docker-compose ps
docker-compose logs postgis
```

### B. Validation des extensions spatiales
```bash
docker-compose exec postgis psql -U medizy_user -d medizy_db -c "
SELECT extname, extversion FROM pg_extension WHERE extname IN ('postgis', 'unaccent', 'pg_trgm');
"
```
*Résultat attendu :*
- `postgis` : version 3.4.x
- `unaccent` : activé (suppression des accents pour les recherches algériennes)
- `pg_trgm` : activé (index GIN pour la tolérance aux fautes de frappe)

---

## 2. Synchronisation et Import SQLite vers PostgreSQL / PostGIS

L'outil dédié `medizy_pipeline/sql/sync_sqlite_to_postgis.py` permet de migrer l'ensemble des données collectées (1 600+ établissements et suggestions) avec transformation géométrique automatique en `GEOMETRY(Point, 4326)`.

### Commande d'exécution :
```bash
python -m medizy_pipeline.sql.sync_sqlite_to_postgis \
  --sqlite-path "E:\medizy_data\medizy_facilities_local.db" \
  --pg-url "postgresql://medizy_user:medizy_password@localhost:5432/medizy_db" \
  --batch-size 500
```

### Vérification de l'Index Spatial GiST en Production :
```sql
-- Vérification que l'index GiST est bien utilisé pour les requêtes de proximité
EXPLAIN ANALYZE
SELECT id, name, type, ST_Distance(geom, ST_SetSRID(ST_MakePoint(3.0588, 36.7528), 4326)::geography) AS dist_m
FROM facilities
WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(3.0588, 36.7528), 4326)::geography, 5000)
ORDER BY dist_m ASC
LIMIT 10;
```

---

## 3. Back-Office de Modération des Suggestions Citoyennes

### A. Sécurisation
Tous les endpoints de modération `/api/v1/admin/*` requièrent une authentification via l'en-tête HTTP :
```http
X-Admin-Api-Key: medizy-admin-secret-key-2026
```
*(Configurable via la variable d'environnement `ADMIN_API_KEY`).*

### B. Spécification des Endpoints de Modération

#### 1. Lister les contributions en attente :
```http
GET /api/v1/admin/suggestions?status=PENDING&limit=50&offset=0
Header: X-Admin-Api-Key: <ADMIN_KEY>
```
*Retourne les structures suggérées avec détection de doublons spatiaux (< 100m) dans le champ `potential_duplicate`.*

#### 2. Approuver une contribution :
```http
POST /api/v1/admin/suggestions/{id}/approve
Header: X-Admin-Api-Key: <ADMIN_KEY>
Content-Type: application/json

{
  "moderator_name": "Dr. Benali (Directeur DSP)",
  "moderation_comment": "Vérifié sur le registre DSP d'Alger.",
  "override_name": null,
  "override_type": "Clinique"
}
```
*Effet :*
- Insertion dans `facilities` avec `source = 'community_suggestion'`, `is_verified = true`, `is_claimed = false`.
- Mise à jour du statut de la suggestion en `APPROVED`.

#### 3. Rejeter une contribution :
```http
POST /api/v1/admin/suggestions/{id}/reject
Header: X-Admin-Api-Key: <ADMIN_KEY>
Content-Type: application/json

{
  "reason": "Établissement fermé définitivement ou informations non conformes.",
  "moderator_name": "Modérateur Régional"
}
```
*Effet :*
- Mise à jour du statut de la suggestion en `REJECTED` avec archivage du motif.

---

## 4. Maintenance & Ingestion Périodique

Pour planifier l'enrichissement cartographique nocturne des 58 wilayas via Cron ou Docker :
```bash
# Ingestion complète avec pause de 2.0s et génération du rapport
python run_ingest.py --all --delay 2.0 --report-file rapport_national_58_wilayas.json
```
Le pipeline est **strictement idempotent** : les structures déjà présentes en base ne sont jamais dupliquées (matching spatial < 100m et `ON CONFLICT (osm_id) DO NOTHING`).
