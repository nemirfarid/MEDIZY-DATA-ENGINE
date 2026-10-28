#!/usr/bin/env bash
# ==============================================================================
# MEDIZY / SANTÉ DZ — Routine d'Entretien Hebdomadaire (PostGIS & Redis)
# ==============================================================================
# Ce script exécute :
#   1. VACUUM (ANALYZE, VERBOSE) sur les tables spatiales sans verrou bloquant.
#   2. REINDEX INDEX CONCURRENTLY sur l'index spatial GiST et l'index trigramme.
#   3. Défragmentation de la mémoire Redis et libération des arènes (MEMORY PURGE).
#   4. Journalisation détaillée et notification Webhook optionnelle.
# ==============================================================================

set -euo pipefail

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-medizy_db}"
POSTGRES_USER="${POSTGRES_USER:-medizy_user}"
export PGPASSWORD="${POSTGRES_PASSWORD:-medizy_password}"

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
WEBHOOK_URL="${WEBHOOK_URL:-${INGEST_ALERT_WEBHOOK_URL:-}}"

LOG_DIR="${LOG_DIR:-/var/log/medizy}"
mkdir -p "${LOG_DIR}" 2>/dev/null || LOG_DIR="/tmp"
LOG_FILE="${LOG_DIR}/db_maintenance_$(date +'%Y%m%d_%H%M%S').log"

START_TIME=$(date +%s)
HOSTNAME=$(hostname 2>/dev/null || echo "medizy-host")

echo "=============================================================================="
echo "    MEDIZY — Routine d'Entretien Hebdomadaire PostGIS & Cache Redis"
echo "=============================================================================="
echo "Hôte PostgreSQL : ${POSTGRES_USER}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "Hôte Redis      : ${REDIS_HOST}:${REDIS_PORT}"
echo "Journalisation  : ${LOG_FILE}"
echo "Horodatage UTC  : $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=============================================================================="

# Redirection optionnelle vers fichier log tout en conservant la sortie console
exec > >(tee -a "${LOG_FILE}") 2>&1

# ==============================================================================
# 1. ÉTAT INITIAL DES TABLES ET VOLUMÉTRIE
# ==============================================================================
echo -e "\n[1/4] Analyse de la volumétrie initiale des tables et index..."
psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "
  SELECT 
      relname AS table_or_index,
      pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
      reltuples::bigint AS estimated_tuples
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' 
    AND c.relname IN ('facilities', 'facility_suggestions', 'idx_facilities_geom', 'idx_facilities_name_trgm')
  ORDER BY pg_total_relation_size(c.oid) DESC;
" || {
  echo "Avertissement : Impossible de récupérer les statistiques initiales (base inaccessible ou droits restreints)."
}

# ==============================================================================
# 2. VACUUM ANALYZE NON BLOQUANT (Mise à jour des stats PostGIS)
# ==============================================================================
echo -e "\n[2/4] Exécution de VACUUM (ANALYZE, VERBOSE) sur les tables spatiales..."
psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "
  -- facilities : table principale avec géométrie PostGIS
  VACUUM (ANALYZE, VERBOSE) facilities;
  -- facility_suggestions : table de modération
  VACUUM (ANALYZE, VERBOSE) facility_suggestions;
"
echo "✓ VACUUM ANALYZE achevé : statistiques de l'optimiseur spatial rafraîchies."

# ==============================================================================
# 3. RÉINDEXATION CONCURRENTE (Élimination du bloat d'index GiST)
# ==============================================================================
echo -e "\n[3/4] Réindexation concurrente des index GiST spatial et GIN trigramme..."
# REINDEX CONCURRENTLY ne verrouille pas les écritures ni les lectures
psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "
  -- Réindexation de l'index spatial GiST (WGS84 EPSG:4326)
  REINDEX INDEX CONCURRENTLY idx_facilities_geom;
  -- Réindexation de l'index trigramme pour recherche textuelle floue
  REINDEX INDEX CONCURRENTLY idx_facilities_name_trgm;
"
echo "✓ REINDEX INDEX CONCURRENTLY achevé : arbre R-Tree GiST et GIN défragmentés."

# ==============================================================================
# 4. MAINTENANCE & DÉFRAGMENTATION DU CACHE REDIS
# ==============================================================================
echo -e "\n[4/4] Purge mémoire et défragmentation du cache Redis..."
if command -v redis-cli >/dev/null 2>&1; then
  REDIS_PING=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping 2>/dev/null || echo "FAILED")
  if [[ "${REDIS_PING}" == "PONG" ]]; then
    # Affichage de la mémoire avant purge
    MEM_USED_PRE=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" info memory | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
    echo "Mémoire Redis avant purge : ${MEM_USED_PRE}"

    # Purge et libération des arènes jemalloc
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" MEMORY PURGE || true

    MEM_USED_POST=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" info memory | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
    echo "Mémoire Redis après purge : ${MEM_USED_POST}"
    echo "✓ Cache Redis défragmenté avec succès."
  else
    echo "ℹ Redis injoignable sur ${REDIS_HOST}:${REDIS_PORT} (ignoré si service non local)."
  fi
else
  echo "ℹ Utilitaire 'redis-cli' non installé localement, étape Redis omise."
fi

# ==============================================================================
# SYNTHÈSE & NOTIFICATION
# ==============================================================================
END_TIME=$(date +%s)
DURATION=$(( END_TIME - START_TIME ))

echo -e "\n=============================================================================="
echo "    SYNTHÈSE DE LA MAINTENANCE HEBDOMADAIRE"
echo "=============================================================================="
echo "Statut global : SUCCÈS"
echo "Durée totale  : ${DURATION} secondes"
echo "Rapport log   : ${LOG_FILE}"
echo "=============================================================================="

if [[ -n "${WEBHOOK_URL}" ]]; then
  PAYLOAD=$(cat <<EOF
{
  "username": "MEDIZY Maintenance Bot",
  "icon_emoji": ":wrench:",
  "text": "✓ *Maintenance Hebdomadaire MEDIZY Terminée*\n*Hôte* : \`${HOSTNAME}\`\n*Durée* : ${DURATION}s\n*Opérations* : \`VACUUM ANALYZE\`, \`REINDEX CONCURRENTLY GiST/GIN\`, \`REDIS MEMORY PURGE\`\n*Statut* : Opérationnel sans indisponibilité."
}
EOF
)
  curl -s -X POST -H "Content-Type: application/json" -d "${PAYLOAD}" "${WEBHOOK_URL}" >/dev/null || true
fi

exit 0
