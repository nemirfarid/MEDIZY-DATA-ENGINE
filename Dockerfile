# Multi-stage Dockerfile pour MEDIZY Backend & Scheduler
FROM python:3.11-slim as base

# Installation des dépendances système nécessaires à PostGIS (GDAL/GEOS) et compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copie des requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pyjwt redis uvicorn

# Copie du code applicatif
COPY medizy_pipeline /app/medizy_pipeline
COPY run_ingest.py /app/run_ingest.py

EXPOSE 8000

# Commande par défaut (FastAPI)
CMD ["uvicorn", "medizy_pipeline.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
