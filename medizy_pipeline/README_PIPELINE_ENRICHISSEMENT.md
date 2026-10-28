# MEDIZY — Pipeline National d'Enrichissement Cartographique & Recherche Géospatiale

Ce module implémente la solution d'architecture complète pour intégrer et afficher **100% des structures de santé publiques et privées** d'Algérie sur les 58 wilayas, sans dépendre exclusivement des inscriptions manuelles.

---

## 1. Architecture Globale

```mermaid
graph TD
    A[Sources de Données Externes] -->|Overpass API / Google Places| B[Pipeline d'Ingestion & Enrichissement]
    C[Citoyens & Praticiens] -->|POST /api/v1/facilities/suggest| D[Table de Modération facility_suggestions]
    
    subgraph "Traitement & Normalisation"
        B --> E[Classificateur Santé Algérie]
        E --> F[Moteur de Déduplication Spatiale & Sémantique]
        F -->|< 100m + Match Nom| G[Ignorer / Enrichir Doublon]
        F -->|Nouveau| H[Insertion is_claimed = false]
    end
    
    subgraph "Stockage Spatial PostGIS"
        H --> I[(PostgreSQL / PostGIS facilities)]
        D -->|Validation Modérateur| I
    end
    
    subgraph "API REST & Consommation"
        I --> J[FastAPI / PostGIS Spatial Queries]
        J -->|ST_DWithin / ST_MakeEnvelope| K[Mobile Flutter & Carte Web]
        K --> L[Badge: Fiche informative publique]
    end
```

---

## 2. Structure des Fichiers

```text
medizy_pipeline/
├── sql/
│   └── 001_facilities_and_suggestions_postgis.sql  # DDL PostGIS, index GiST, trigger et procédures
├── enrichment/
│   ├── classifier.py                                # Classification CHU, EPH, EPSP, Clinique, Urgences
│   ├── deduplication.py                             # Haversine & Jaccard/SequenceMatcher (< 100m)
│   ├── url_parser.py                                # Extraction regex de coordonnées depuis Google Maps
│   ├── osm_overpass.py                              # Client Overpass avec failover multi-miroirs
│   ├── google_places.py                             # Client Google Places (Nearby & Text Search)
│   └── ingest_pipeline.py                           # Orchestrateur national sur les 58 wilayas
├── api/
│   ├── schemas.py                                   # Modèles Pydantic v2 (Requêtes, Réponses, Badges)
│   ├── db.py                                        # Couche d'accès aux données PostGIS (et fallback SQLite)
│   ├── routes/
│   │   ├── facilities.py                            # GET /search, GET /nearby, GET /{id}
│   │   └── suggestions.py                           # POST /suggest (Crowdsourcing)
│   └── main.py                                      # Application FastAPI avec CORS et Swagger
└── tests/
    └── test_pipeline.py                             # Suite complète de tests unitaires & intégration
```

---

## 3. Guide de Démarrage Rapide

### A. Déploiement du Schéma PostGIS
```bash
psql -h localhost -U medizy_user -d medizy_db -f medizy_pipeline/sql/001_facilities_and_suggestions_postgis.sql
```

### B. Lancement de l'Ingestion Automatique
Pour lancer l'ingestion sur les 58 wilayas via OpenStreetMap (gratuit et sans clé API) :
```bash
python -m medizy_pipeline.enrichment.ingest_pipeline --db-url "postgresql://medizy_user:password@localhost:5432/medizy_db"
```

Pour cibler des wilayas spécifiques (ex: Alger, Oran, Constantine) :
```bash
python -m medizy_pipeline.enrichment.ingest_pipeline --wilayas 16 31 25 --db-url "postgresql://medizy_user:password@localhost:5432/medizy_db"
```

Pour activer le double enrichissement Google Places (clé `GOOGLE_PLACES_API_KEY` requise) :
```bash
python -m medizy_pipeline.enrichment.ingest_pipeline --wilayas 16 --google
```

### C. Lancement du Serveur API FastAPI
```bash
uvicorn medizy_pipeline.api.main:app --host 0.0.0.0 --port 8000 --reload
```
* Swagger UI : `http://localhost:8000/docs`
* OpenAPI JSON : `http://localhost:8000/openapi.json`
* Health Check : `http://localhost:8000/health`

### D. Exécution des Tests
```bash
python -m unittest medizy_pipeline/tests/test_pipeline.py
```
