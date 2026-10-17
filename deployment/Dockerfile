# ==============================================================================
# SANTÉ DZ / MEDIZY — DOCKERFILE INDUSTRIEL ULTRA-LÉGER (Phase 7)
# ==============================================================================
# Image de base minimale sans compilateurs ni packages inutiles
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="Santé DZ / Medizy Core Team"
LABEL version="1.0.14-deploy"
LABEL description="Micro-service API REST & Cache Mobile Santé DZ Medizy"

# Variables d'environnement standardisées
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    MEDIZY_DB_PATH=/app/medizy_scraper.db

WORKDIR /app

# Création d'un utilisateur non-root non privilégié pour la sécurité en production
RUN groupadd -g 10001 medizy && \
    useradd -u 10001 -g medizy -s /bin/sh -m medizy

# Copie des composants applicatifs essentiels (aucun package pip externe requis)
COPY --chown=medizy:medizy api_server.py /app/
COPY --chown=medizy:medizy medizy_search.py /app/
COPY --chown=medizy:medizy export_mobile_cache.py /app/
COPY --chown=medizy:medizy communes_algerie_officielles.json /app/
COPY --chown=medizy:medizy exports/mobile/ /app/exports/mobile/
COPY --chown=medizy:medizy tools/ /app/tools/

# Bascule vers l'utilisateur non-root
USER medizy

# Exposition du port REST standard
EXPOSE 8000

# Healthcheck natif sans outil tiers (curl/wget non requis, utilisation de urllib python)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3).getcode() == 200 else 1)"

# Démarrage du serveur REST en écoute sur toutes les interfaces
CMD ["python3", "api_server.py", "--host", "0.0.0.0", "--port", "8000"]
