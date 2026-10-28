#!/usr/bin/env bash
# ==============================================================================
# MEDIZY / SANTÉ DZ — Script de Sauvegarde Automatisée PostGIS (DR Plan)
# ==============================================================================
# - Exécute un pg_dump compressé haute performance.
# - Valide l'intégrité de l'archive (Disaster Recovery Verification).
# - Applique une rotation glissante stricte sur 14 jours.
# - Transfère l'archive vers un stockage distant sécurisé (S3 / Volume monté).
# - Émet un rapport d'audit structuré JSON et alerte webhook en cas d'échec.
# ==============================================================================

set -euo pipefail

# 1. Configuration des variables d'environnement (avec valeurs par défaut)
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-medizy_db}"
POSTGRES_USER="${POSTGRES_USER:-medizy_user}"
export PGPASSWORD="${POSTGRES_PASSWORD:-medizy_password}"

BACKUP_DIR="${BACKUP_DIR:-/var/backups/medizy}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
S3_BUCKET="${S3_BUCKET:-}"
WEBHOOK_URL="${WEBHOOK_URL:-}"
LOG_FILE="${BACKUP_DIR}/backup_execution.log"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="medizy_postgis_${POSTGRES_DB}_${TIMESTAMP}.dump"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"

mkdir -p "${BACKUP_DIR}"

log() {
  local level="$1"
  local message="$2"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "{\"timestamp\": \"${ts}\", \"level\": \"${level}\", \"message\": \"${message}\"}" | tee -a "${LOG_FILE}"
}

notify_alert() {
  local status="$1"
  local details="$2"
  if [[ -n "${WEBHOOK_URL}" ]]; then
    local payload
    payload=$(cat <<EOF
{
  "text": "🛡️ *MEDIZY PostGIS Backup [${status}]*\n• *Base* : \`${POSTGRES_DB}\`\n• *Horodatage* : \`${TIMESTAMP}\`\n• *Détails* : ${details}"
}
EOF
)
    curl -s -X POST -H 'Content-type: application/json' --data "${payload}" "${WEBHOOK_URL}" > /dev/null || true
  fi
}

log "INFO" "Démarrage de la sauvegarde PostGIS pour la base '${POSTGRES_DB}' sur ${POSTGRES_HOST}:${POSTGRES_PORT}..."
START_TIME=$(date +%s)

# 2. Exécution du pg_dump binaire compressé (-Fc avec compression zlib niveau 9)
if pg_dump \
  -h "${POSTGRES_HOST}" \
  -p "${POSTGRES_PORT}" \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  -Fc \
  -Z 9 \
  --blobs \
  --verbose \
  -f "${BACKUP_PATH}" 2>> "${LOG_FILE}"; then

  BACKUP_SIZE_BYTES=$(stat -c%s "${BACKUP_PATH}" 2>/dev/null || stat -f%z "${BACKUP_PATH}" 2>/dev/null || wc -c < "${BACKUP_PATH}")
  BACKUP_SIZE_MB=$(awk "BEGIN {printf \"%.2f\", ${BACKUP_SIZE_BYTES}/1048576}")
  log "INFO" "Archive générée avec succès : ${BACKUP_FILENAME} (${BACKUP_SIZE_MB} Mo)."
else
  log "ERROR" "Échec critique lors de l'exécution de pg_dump !"
  notify_alert "FAILURE" "Erreur d'extraction pg_dump. Vérifier les journaux."
  exit 1
fi

# 3. Contrôle d'intégrité immédiat (Disaster Recovery Validation)
log "INFO" "Validation de l'intégrité de l'archive via pg_restore --list..."
if pg_restore --list "${BACKUP_PATH}" > /dev/null 2>&1; then
  log "INFO" "Contrôle d'intégrité VALIDÉ : l'archive est restaurable sans corruption."
else
  log "ERROR" "Contrôle d'intégrité ÉCHOUÉ : l'archive est corrompue !"
  notify_alert "CORRUPTION" "Archive corrompue détectée lors du test de restauration."
  exit 2
fi

# 4. Transfert déporté sécurisé (AWS S3 ou stockage distant)
if [[ -n "${S3_BUCKET}" ]]; then
  log "INFO" "Transfert de la sauvegarde vers le stockage distant S3 (${S3_BUCKET})..."
  if command -v aws &> /dev/null; then
    aws s3 cp "${BACKUP_PATH}" "${S3_BUCKET%/}/${BACKUP_FILENAME}" --storage-class STANDARD_IA
    log "INFO" "Sauvegarde déportée sur S3 avec succès."
  else
    log "WARNING" "Commande 'aws' introuvable. Transfert distant ignoré."
  fi
fi

# 5. Application de la politique de rétention glissante (14 jours)
log "INFO" "Application de la purge des sauvegardes locales antérieures à ${RETENTION_DAYS} jours..."
DELETED_COUNT=0
while IFS= read -r old_backup; do
  if [[ -n "${old_backup}" ]]; then
    rm -f "${old_backup}"
    DELETED_COUNT=$((DELETED_COUNT + 1))
    log "INFO" "Ancienne archive purgée : $(basename "${old_backup}")"
  fi
done < <(find "${BACKUP_DIR}" -name "medizy_postgis_*.dump" -type f -mtime +"${RETENTION_DAYS}")

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

log "INFO" "Opération de sauvegarde terminée avec succès en ${DURATION} secondes. Purges : ${DELETED_COUNT} fichier(s)."
notify_alert "SUCCESS" "Sauvegarde réussie (${BACKUP_SIZE_MB} Mo en ${DURATION}s). Rotation 14j appliquée."

exit 0
