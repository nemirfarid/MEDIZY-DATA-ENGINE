# ==============================================================================
# SANTÉ DZ / MEDIZY — RUNBOOK DE PRODUCTION & DÉPLOIEMENT INDUSTRIEL
# ==============================================================================
# Programme National Sanitaire — République Algérienne Démocratique et Populaire
# Version : 1.0.15-extended | Statut : Certifié Production Phase 8 | Date : Octobre 2026
# ==============================================================================

## 1. FICHE D'IDENTITÉ & CERTIFICATION DE L'ACTIF DE DONNÉES

| Paramètre | Spécification Officielle |
| :--- | :--- |
| **Actif de données** | `medizy_scraper.db` (SQLite 3 WAL compatible) |
| **Volume certifié** | **35 832 établissements sanitaires** |
| **Couverture territoriale** | **58 wilayas d'Algérie** (100% complètes, 553 communes) |
| **Couverture géolocalisée (GPS)** | **100.00%** (35 832 / 35 832 coordonnées décimales valides) |
| **Couverture téléphonique** | **17 125 contacts directs** |
| **Empreinte cryptographique SHA-256** | `b81a08f36a3e6048016a2e0b095128040fccc80022bc566f07f9ab822c0ab791` |
| **Mode d'accès en exécution** | **Lecture seule stricte (`file:...db?mode=ro`, `uri=True`)** |
| **Dépendances pip requises** | **0 package externe** (100% Python Standard Library) |

---

## 2. MODÈLE DE CONTENEURISATION DOCKER LÉGÈRE

### 2.1. Principes d'architecture
- **Image de base minimale** : `python:3.11-slim` sans compilateur GCC ni package superflu (taille d'image < 150 Mo).
- **Sécurité et durcissement** : Exécution exclusive sous utilisateur non-root non privilégié (`medizy:10001`).
- **Isolation de la donnée** : Montage bind-mount externe de la base SQLite en mode lecture seule stricte (`:ro`).
- **Healthcheck natif** : Contrôle toutes les 30s via la bibliothèque standard `urllib` sans dépendance vers `curl` ou `wget`.

### 2.2. Lancement via Docker Compose (Recommandé)

Le fichier `deployment/docker-compose.yml` applique les restrictions de ressources matérielles :
- **CPU** : Limité à 0.5 cœur.
- **RAM** : Plafonnée à 256 Mo (réservation 64 Mo).
- **Restart Policy** : `always`.

```bash
# Se placer dans le répertoire racine du projet
cd /opt/medizy

# Démarrer le conteneur en arrière-plan
docker compose -f deployment/docker-compose.yml up -d

# Inspecter l'état et le statut du healthcheck
docker compose -f deployment/docker-compose.yml ps

# Consulter les journaux en direct
docker compose -f deployment/docker-compose.yml logs -f --tail=100
```

### 2.3. Lancement direct via Docker CLI

```bash
# Construction de l'image
docker build -t medizy-api:1.0.14 -f deployment/Dockerfile .

# Démarrage avec limitation de ressources et montage read-only
docker run -d \
  --name medizy-api \
  --restart always \
  --cpus 0.5 \
  --memory 256m \
  -p 8000:8000 \
  -v $(pwd)/medizy_scraper.db:/app/medizy_scraper.db:ro \
  medizy-api:1.0.14
```

---

## 3. DÉPLOIEMENT VPS CLOUD LINUX (SYSTEMD SERVICE)

Pour l'hébergement sur serveur Ubuntu 22.04 / 24.04 LTS ou Debian 12.

### 3.1. Préparation de l'environnement

```bash
# 1. Création de l'utilisateur système dédié sans shell de connexion
sudo useradd -r -s /usr/sbin/nologin -d /opt/medizy medizy

# 2. Déploiement de l'arborescence applicative
sudo mkdir -p /opt/medizy
sudo cp -r api_server.py medizy_search.py export_mobile_cache.py communes_algerie_officielles.json tools/ exports/ /opt/medizy/
sudo cp medizy_scraper.db /opt/medizy/

# 3. Restriction des droits (lecture seule pour l'utilisateur medizy)
sudo chown -R medizy:medizy /opt/medizy
sudo chmod 440 /opt/medizy/medizy_scraper.db
```

### 3.2. Installation et activation de l'unité Systemd

```bash
# Copie du fichier d'unité
sudo cp deployment/medizy.service /etc/systemd/system/medizy.service

# Rechargement du démon systemd
sudo systemctl daemon-reload

# Activation au démarrage système et lancement immédiat
sudo systemctl enable --now medizy

# Vérification du statut opérationnel
sudo systemctl status medizy

# Consultation des journaux systemd
sudo journalctl -u medizy -f -o cat
```

---

## 4. DÉPLOIEMENT SERVEUR WINDOWS (SERVICE D'ARRIÈRE-PLAN)

Pour l'exploitation sur Windows Server ou poste de supervision sans interface graphique interactive.

### 4.1. Emplacements physiques standardisés
- **Workspace applicatif** : `C:\SANTE_DZ_SCRAPER`
- **Stockage sécurisé & Journaux** : `D:\SANTE_DZ_EXPORTS\logs\`
  * `D:\SANTE_DZ_EXPORTS\logs\api_service.log` : Journaux d'activité et requêtes HTTP.
  * `D:\SANTE_DZ_EXPORTS\logs\api_service.pid` : Identifiant du processus en cours.

### 4.2. Commandes de pilotage PowerShell

```powershell
# 1. Démarrer le service en arrière-plan (sans console UI)
powershell.exe -ExecutionPolicy Bypass -File deployment\start_windows_service.ps1 -Action start

# 2. Inspecter l'état et vérifier la connectivité HTTP
powershell.exe -ExecutionPolicy Bypass -File deployment\start_windows_service.ps1 -Action status

# 3. Redémarrer le service
powershell.exe -ExecutionPolicy Bypass -File deployment\start_windows_service.ps1 -Action restart

# 4. Arrêter le service
powershell.exe -ExecutionPolicy Bypass -File deployment\start_windows_service.ps1 -Action stop
```

---

## 5. MONITORING ACTIF & AUTORÉPARATION (`tools/health_monitor.py`)

Le script `tools/health_monitor.py` surveille continuellement l'état de l'API et peut déclencher une autoréparation automatique.

### 5.1. Métriques et points de contrôle inspectés
1. **Intégrité SQLite & Volume** (`/api/v1/health`) : Valide `sqlite_integrity == "ok"`, `total_entries >= 30000`, et l'empreinte SHA-256.
2. **Métriques nationales** (`/api/v1/stats`) : Valide les 58 wilayas et la ventilation par source.
3. **Cache mobile compressé** (`/api/v1/cache/national`) : Valide les magic bytes GZIP (`\x1f\x8b`) et le flux binaire.
4. **Seuil de latence** : Si le temps de réponse moyen dépasse **200 ms**, le service est classé **DEGRADED**.

### 5.2. Modes d'exécution

```bash
# Vérification ponctuelle (One-shot) pour pipeline CI/CD ou healthcheck
python tools/health_monitor.py --once --url http://127.0.0.1:8000

# Surveillance cyclique continue avec autoréparation (redémarrage en cas d'arrêt)
python tools/health_monitor.py \
  --url http://127.0.0.1:8000 \
  --interval 15 \
  --max-latency-ms 200 \
  --auto-restart \
  --report-file D:\SANTE_DZ_EXPORTS\logs\health_report.json
```

---

## 6. PROCÉDURE DE MISE À JOUR À CHAUD SANS INTERRUPTION (ZERO DOWNTIME)

Pour mettre à jour la base de données ou le code de l'API sans interruption pour les applications consommatrices :

### 6.1. Préparation et validation hors-ligne
1. Télécharger ou générer la nouvelle base sur le volume de staging :
   `D:\SANTE_DZ_EXPORTS\staging\medizy_scraper_candidate.db`.
2. Valider l'intégrité et exécuter les tests de non-régression :
   ```bash
   $env:MEDIZY_DB_PATH="D:\SANTE_DZ_EXPORTS\staging\medizy_scraper_candidate.db"
   .\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
   ```
3. Calculer et enregistrer l'empreinte SHA-256 certifiée.

### 6.2. Bascule atomique sous Docker
```bash
# 1. Remplacer la base de données cible
cp D:/SANTE_DZ_EXPORTS/staging/medizy_scraper_candidate.db /opt/medizy/medizy_scraper.db

# 2. Relancer le conteneur avec compose (démarrage du nouveau conteneur avant extinction de l'ancien)
docker compose -f deployment/docker-compose.yml up -d --no-deps medizy-api
```

### 6.3. Bascule atomique sous Linux Systemd
```bash
# Rechargement transparent
sudo cp /opt/medizy/medizy_scraper_candidate.db /opt/medizy/medizy_scraper.db
sudo systemctl reload-or-restart medizy
```

---

## 7. PLAN DE REPRISE D'ACTIVITÉ & RESTAURATION D'URGENCE (DRP)

En cas de corruption du système de fichiers ou d'incident sur le disque `C:\` :

### 7.1. Inventaire des sauvegardes d'or certifiées sur `D:\`

| Sauvegarde | Emplacement Physique | SHA-256 | Description |
| :--- | :--- | :--- | :--- |
| **Baseline Phase 1** | `D:\SANTE_DZ_EXPORTS\backups\medizy_scraper_phase1_baseline.db` | `948fda84d6375b6b1dbd7ba822cdcfe09f7301f81f8779bc803e717b582c493d` | 23 669 établissements bruts |
| **Production Phase 4** | `D:\SANTE_DZ_EXPORTS\backups\medizy_scraper_pre_phase6.db` | `69b94b3ca03d80d5ea33f8395482c6763e72d1fba5c491300b0e92dcd6d12e65` | 23 669 assainis 100% |
| **Production Phase 6/7** | `D:\SANTE_DZ_EXPORTS\backups\medizy_scraper_pre_phase8.db` | `6690141cd6223f953c624801edf7472714bec116b8f54f5ec4840c78d6168601` | 30 568 établissements certifiés |
| **Production Actuelle (Phase 8)** | `D:\SANTE_DZ_EXPORTS\backups\medizy_production_certified_35832.db` | `b81a08f36a3e6048016a2e0b095128040fccc80022bc566f07f9ab822c0ab791` | **35 832 établissements (58 wilayas, 100% GPS)** |

### 7.2. Procédure de restauration bit-à-bit pas-à-pas

```powershell
# 1. Arrêter le service API en cours
powershell.exe -File deployment\start_windows_service.ps1 -Action stop

# 2. Restaurer la copie certifiée depuis D:\
Copy-Item -Path "D:\SANTE_DZ_EXPORTS\backups\medizy_production_certified_35832.db" `
          -Destination "C:\SANTE_DZ_SCRAPER\medizy_scraper.db" -Force

# 3. Contrôler rigoureusement l'empreinte SHA-256
$hash = (Get-FileHash -Path "C:\SANTE_DZ_SCRAPER\medizy_scraper.db" -Algorithm SHA256).Hash.ToLower()
if ($hash -ne "b81a08f36a3e6048016a2e0b095128040fccc80022bc566f07f9ab822c0ab791") {
    Write-Error "ÉCHEC CRITIQUE : L'empreinte SHA-256 restaurée ne correspond pas au scellement officiel !"
    exit 1
}

# 4. Exécuter le test d'intégrité SQLite
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('C:/SANTE_DZ_SCRAPER/medizy_scraper.db'); assert c.execute('PRAGMA integrity_check;').fetchone()[0] == 'ok'; print('[SUCCÈS] Intégrité SQLite certifiée')"

# 5. Redémarrer le service
powershell.exe -File deployment\start_windows_service.ps1 -Action start

# 6. Valider le healthcheck
python tools/health_monitor.py --once
```

---

## 8. MATRICE DE TESTS ET QUALIFICATION DE LA PHASE 7

La suite consolidée de **41 tests unitaires et d'intégration** valide 100% des exigences :
- Tests de recherche géospatiale et plein texte : **10/10 OK**
- Tests de synchronisation du cache mobile : **2/2 OK**
- Tests des endpoints de l'API REST : **13/13 OK**
- Tests d'industrialisation et benchmarks : **4/4 OK**
- Tests d'expansion et non-régression Phase 6 : **5/5 OK**
- Tests de conteneurisation et services Phase 7 : **7/7 OK**
- **Résultat global** : **41/41 réussis (100% succès)**.
