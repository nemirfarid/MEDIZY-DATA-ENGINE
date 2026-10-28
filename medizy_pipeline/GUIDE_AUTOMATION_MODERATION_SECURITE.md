# MEDIZY — Guide Production : Automatisation Nocturne, Dashboard de Modération & Sécurité JWT / Redis

Ce guide opérationnel décrit les trois volets majeurs déployés pour la mise en production de la plateforme de santé **MEDIZY** (référentiel national des établissements de santé en Algérie).

---

## 1. Automatisation des Mises à Jour Périodiques (Scheduler Nocturne)

### A. Architecture et Fonctionnalités
- **Orchestrateur** : [`cron_ingest.py`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/scheduler/cron_ingest.py) & [`celery_tasks.py`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/scheduler/celery_tasks.py)
- **Heure d'exécution programmée** : Chaque nuit à **02h00** (période de faible affluence).
- **Throttling & Préservation des Performances** :
  - Temporisation paramétrable (`--delay 3.0`) entre requêtes wilayas.
  - Absence de locks exclusifs sur la table `facilities`.
- **Résilience Réseau & Failover Overpass** :
  - Rotation automatique en cas de timeout (30s) ou d'erreur 429/504 à travers 4 miroirs mondiaux certifiés :
    1. `https://overpass-api.de/api/interpreter`
    2. `https://lz4.overpass-api.de/api/interpreter`
    3. `https://overpass.kumi.systems/api/interpreter`
    4. `https://overpass.private.coffee/api/interpreter`
- **Journalisation Structurée (Audit Logging)** :
  - Émission d'événements JSON Lines dans `medizy_ingest_audit.jsonl` :
    `INGEST_CYCLE_STARTED`, `MIRROR_FAILOVER_TRIGGERED`, `INGEST_CYCLE_FINISHED`.
  - Notification webhook prête pour Slack / Microsoft Teams / Discord via `INGEST_ALERT_WEBHOOK_URL`.

### B. Commandes d'Exécution

#### 1. Lancement en Démon Autonome (Docker ou VM dédiée) :
```bash
python -m medizy_pipeline.scheduler.cron_ingest --daemon --time 02:00 --delay 3.0
```

#### 2. Déclenchement One-Shot (Crontab Linux standard) :
Dans `/etc/cron.d/medizy-ingest` :
```cron
# Exécution nocturne à 02h00 chaque jour
0 2 * * * medizy /opt/medizy/venv/bin/python -m medizy_pipeline.scheduler.cron_ingest --now --all --delay 3.0 >> /var/log/medizy_cron.log 2>&1
```

#### 3. Intégration Celery Beat (Kubernetes / Docker Swarm) :
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'medizy-nightly-ingest': {
        'task': 'medizy_pipeline.scheduler.celery_tasks.task_nightly_health_ingest',
        'schedule': crontab(hour=2, minute=0),
        'kwargs': {'all_wilayas': True, 'delay_seconds': 3.0},
    },
}
```

---

## 2. Tableau de Bord de Modération & Comparateur Cartographique

### A. Composants Frontend React / TypeScript
Les composants créés se situent dans [`medizy_pipeline/frontend/`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/frontend/) :
- [`AdminModerationDashboard.tsx`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/frontend/AdminModerationDashboard.tsx) : Tableau de bord de modération avec :
  - Écran de connexion sécurisé JWT.
  - Compteurs KPI (En attente, Alertes doublons < 100m, Couverture 58 wilayas, Quota Rate-Limit).
  - Barre d'outils avec filtres dynamiques (`PENDING`, `APPROVED`, `REJECTED`, recherche textuelle, toggle "Doublons uniquement").
  - Modale d'approbation (avec sélection de la typologie officielle et notes de certification).
  - Modale de rejet avec motifs prédéfinis.
- [`DuplicateComparisonMap.tsx`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/frontend/DuplicateComparisonMap.tsx) : Vue miniature comparative permettant de visualiser :
  - Le canevas cartographique SVG avec projection métrique locale.
  - Le rayon d'exclusion critique de **100 mètres** autour de l'établissement existant.
  - Le vecteur de distance avec badge kilométrique / métrique précis.
  - Marqueur bleu pulsant pour la proposition citoyenne vs marqueur vert certifié pour l'existant.
  - Tableau comparatif côte à côte des attributs (Nom, Typologie, Commune, Adresse, Téléphone, Source).
- [`adminApi.ts`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/frontend/adminApi.ts) : Client API gérant le cycle de vie du jeton JWT (`localStorage`), l'injection de l'en-tête `Authorization: Bearer <token>`, et l'extraction des en-têtes `X-RateLimit-*`.

---

## 3. Sécurité, Authentification JWT & Rate Limiting Redis

### A. Authentification RFC 7519 (JWT)
1. **Endpoint de Connexion** :
   ```http
   POST /api/v1/admin/auth/login
   Content-Type: application/json

   {
     "username": "admin@medizy.dz",
     "password": "MedizyAdmin2026!"
   }
   ```
2. **Réponse 200 OK** :
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "expires_in": 86400,
     "role": "superadmin",
     "admin_name": "Administrateur MEDIZY"
   }
   ```
3. **Accès aux routes protégées** :
   ```http
   GET /api/v1/admin/suggestions?status=PENDING
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
   *(Rétrocompatibilité préservée avec l'en-tête `X-Admin-Api-Key` pour les scripts de monitoring).*

### B. Protection Anti-Brute-Force & Limitation de Débit (Redis + Fallback In-Memory)
- **Architecture** : [`rate_limiter.py`](file:///c:/SANTE_DZ_SCRAPER/medizy_pipeline/api/rate_limiter.py)
- **Règles configurées** :
  - `login_rate_limiter` : **5 requêtes / minute** par adresse IP.
    *(Bloque immédiatement les attaques par dictionnaire ou force brute avec code HTTP 429).*
  - `admin_action_rate_limiter` : **60 requêtes / minute** par administrateur.
- **En-têtes RFC standards retournés** :
  - `X-RateLimit-Limit` : Quota accordé sur la fenêtre glissante.
  - `X-RateLimit-Remaining` : Nombre de requêtes restantes avant blocage.
  - `X-RateLimit-Reset` : Temps UNIX de réinitialisation de la fenêtre.
- **Résilience** : Bascule transparente sur une fenêtre glissante en mémoire locale si le serveur Redis est indisponible ou non démarré en développement.

---

## 4. Déploiement Conteneurisé avec Docker Compose

L'ensemble de la pile de production (PostGIS + Redis + FastAPI API + Ingest Scheduler) est orchestré dans [`docker-compose.yml`](file:///c:/SANTE_DZ_SCRAPER/docker-compose.yml) :

```bash
# Démarrer tous les services en production
docker-compose up -d

# Vérifier la santé des conteneurs
docker-compose ps

# Suivre les journaux du planificateur nocturne
docker-compose logs -f ingest-scheduler
```
