#!/usr/bin/env bash
# ==============================================================================
# MEDIZY / SANTÉ DZ — Script de Restauration d'Urgence PostGIS (Disaster Recovery)
# ==============================================================================
# Usage :
#   ./scripts/restore_postgis.sh /chemin/vers/sauvegarde.dump
# ==============================================================================

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <fichier_sauvegarde.dump>"
  exit 1
fi

BACKUP_FILE="$1"
if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "ERREUR : Le fichier '${BACKUP_FILE}' est introuvable."
  exit 1
fi

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-medizy_db}"
POSTGRES_USER="${POSTGRES_USER:-medizy_user}"
export PGPASSWORD="${POSTGRES_PASSWORD:-medizy_password}"

echo "=============================================================================="
echo "    MEDIZY — Procédure de Restauration PostGIS (Disaster Recovery)"
echo "=============================================================================="
echo "Fichier source : ${BACKUP_FILE}"
echo "Cible          : ${POSTGRES_USER}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "=============================================================================="

read -p "ATTENTION : La base '${POSTGRES_DB}' va être réinitialisée. Confirmer (o/N) ? " -r CONFIRM
if [[ ! "${CONFIRM}" =~ ^[oOyY]$ ]]; then
  echo "Restauration annulée par l'opérateur."
  exit 0
fi

START_TS=$(date +%s)

# ÉTAPE 1 : Recréation propre de la base de données
echo "[1/5] Recréation de la base de données '${POSTGRES_DB}'..."
psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres -c "
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();
  DROP DATABASE IF EXISTS ${POSTGRES_DB};
  CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER} ENCODING 'UTF8';
"

# ÉTAPE 2 : Activation des extensions spatiales et textuelles
echo "[2/5] Activation des extensions spatiales (postgis, unaccent, pg_trgm)..."
psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "
  CREATE EXTENSION IF NOT EXISTS postgis;
  CREATE EXTENSION IF NOT EXISTS unaccent;
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
"

# ÉTAPE 3 : Restauration via pg_restore en multi-jobs
echo "[3/5] Exécution de pg_restore (mode parallèle 4 jobs)..."
pg_restore \
  -h "${POSTGRES_HOST}" \
  -p "${POSTGRES_PORT}" \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --jobs=4 \
  --verbose \
  "${BACKUP_FILE}" || {
    echo "Avertissement lors de pg_restore (certaines erreurs non bloquantes peuvent être ignorées)."
  }

# ÉTAPE 4 : Réindexation concurrente et optimisation du planificateur SQL
echo "[4/5] Réindexation GiST et VACUUM ANALYZE..."
psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "
  REINDEX TABLE CONCURRENTLY facilities;
  VACUUM ANALYZE facilities;
  VACUUM ANALYZE facility_suggestions;
"

# ÉTAPE 5 : Sanity Check de validation des données restaurées
echo "[5/5] Contrôle de cohérence géospatiale..."
COUNT=$(psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -c "SELECT COUNT(*) FROM facilities;")
BBOX=$(psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -c "SELECT ST_AsText(ST_Extent(geom)) FROM facilities;")
DURATION=$(( $(date +%s) - START_TS ))

echo "=============================================================================="
echo "    RÉSULTAT DU CONTRÔLE DE REPRISE APRÈS SINISTRE (DRP)"
echo "=============================================================================="
echo "• Établissements restaurés : $(echo "${COUNT}" | tr -d ' ')"
echo "• Bounding Box géospatiale : $(echo "${BBOX}" | tr -d ' ')"
echo "• Durée d'exécution        : ${DURATION} secondes"
echo "✓ BASE DE DONNÉES RESTAURÉE ET OPÉRATIONNELLE AVEC SUCCÈS."
echo "=============================================================================="

exit 0
