#!/usr/bin/env bash
# ==============================================================================
# MEDIZY / SANTÉ DZ — Sonde de Surveillance de Fraîcheur des Sauvegardes
# ==============================================================================
# Ce script vérifie :
#   1. La présence d'une archive PostGIS .dump datant de moins de 26 heures.
#   2. L'intégrité non destructive de l'archive via `pg_restore --list`.
#   3. L'exportation des métriques Prometheus (medizy_backup_success_status).
#   4. L'envoi d'une alerte Webhook critique en cas d'anomalie ou de retard.
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/medizy}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-26}"
MAX_AGE_SECONDS=$(( MAX_AGE_HOURS * 3600 ))
WEBHOOK_URL="${WEBHOOK_URL:-${INGEST_ALERT_WEBHOOK_URL:-}}"
PROMETHEUS_TEXTFILE_DIR="${PROMETHEUS_TEXTFILE_DIR:-/var/lib/prometheus/node-exporter}"
STATE_FILE="${BACKUP_DIR}/backup_state.json"

NOW=$(date +%s)
HOSTNAME=$(hostname 2>/dev/null || echo "medizy-host")

echo "=============================================================================="
echo "    MEDIZY — Contrôle de Fraîcheur & Intégrité des Sauvegardes PostGIS"
echo "=============================================================================="
echo "Répertoire analysé : ${BACKUP_DIR}"
echo "Seuil maximal      : ${MAX_AGE_HOURS} heures (${MAX_AGE_SECONDS} secondes)"
echo "Date du contrôle   : $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=============================================================================="

send_alert() {
  local error_msg="$1"
  echo "🚨 ALERTE CRITIQUE : ${error_msg}" >&2

  # Écriture de l'état d'échec pour Prometheus
  mkdir -p "${BACKUP_DIR}" 2>/dev/null || true
  cat <<EOF > "${STATE_FILE}"
{
  "checked_at": $(date +%s),
  "is_valid": false,
  "last_backup_timestamp": 0,
  "error": "${error_msg}"
}
EOF

  if [[ -d "${PROMETHEUS_TEXTFILE_DIR}" ]]; then
    cat <<EOF > "${PROMETHEUS_TEXTFILE_DIR}/medizy_backup_freshness.prom.$$"
# HELP medizy_last_backup_timestamp Timestamp Unix de la dernière sauvegarde PostGIS certifiée valide
# TYPE medizy_last_backup_timestamp gauge
medizy_last_backup_timestamp 0
# HELP medizy_backup_success_status Statut de conformité de la sauvegarde (1 = conforme, 0 = alerte)
# TYPE medizy_backup_success_status gauge
medizy_backup_success_status 0
# HELP medizy_backup_age_seconds Âge en secondes de la dernière sauvegarde certifiée
# TYPE medizy_backup_age_seconds gauge
medizy_backup_age_seconds -1
EOF
    mv "${PROMETHEUS_TEXTFILE_DIR}/medizy_backup_freshness.prom.$$" "${PROMETHEUS_TEXTFILE_DIR}/medizy_backup_freshness.prom"
  fi

  # Envoi Webhook
  if [[ -n "${WEBHOOK_URL}" ]]; then
    local payload
    payload=$(cat <<EOF
{
  "username": "MEDIZY Backup Monitor",
  "icon_emoji": ":warning:",
  "text": "🚨 *ALERTE CRITIQUE SAUVEGARDE MEDIZY*\n*Hôte* : \`${HOSTNAME}\`\n*Erreur* : ${error_msg}\n*Action requise* : Vérifier le cron de backup (\`backup_postgis.sh\`) et l'espace disque."
}
EOF
)
    curl -s -X POST -H "Content-Type: application/json" -d "${payload}" "${WEBHOOK_URL}" || true
  fi
}

# 1. Recherche du fichier le plus récent dans le répertoire de sauvegarde
if [[ ! -d "${BACKUP_DIR}" ]]; then
  send_alert "Le répertoire de sauvegarde '${BACKUP_DIR}' est introuvable."
  exit 1
fi

LATEST_DUMP=$(find "${BACKUP_DIR}" -maxdepth 1 -type f -name "*.dump" -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | awk '{print $2}' || true)

# Secours si printf n'est pas supporté (ex: macOS ou environnement BSD)
if [[ -z "${LATEST_DUMP}" ]]; then
  LATEST_DUMP=$(ls -t "${BACKUP_DIR}"/*.dump 2>/dev/null | head -n 1 || true)
fi

if [[ -z "${LATEST_DUMP}" || ! -f "${LATEST_DUMP}" ]]; then
  send_alert "Aucune archive .dump trouvée dans '${BACKUP_DIR}'."
  exit 1
fi

# 2. Mesure de l'âge du fichier
if stat -c %Y "${LATEST_DUMP}" >/dev/null 2>&1; then
  FILE_MTIME=$(stat -c %Y "${LATEST_DUMP}")
else
  FILE_MTIME=$(stat -f %m "${LATEST_DUMP}")
fi

AGE_SECONDS=$(( NOW - FILE_MTIME ))
AGE_HOURS=$(awk "BEGIN {printf \"%.2f\", ${AGE_SECONDS}/3600}")
FILE_SIZE_MB=$(du -m "${LATEST_DUMP}" | cut -f1)

echo "Fichier détecté : ${LATEST_DUMP}"
echo "Taille archive  : ${FILE_SIZE_MB} Mo"
echo "Âge mesuré      : ${AGE_HOURS} heures (${AGE_SECONDS}s)"

# 3. Contrôle du seuil d'âge (< 26h)
if [[ ${AGE_SECONDS} -gt ${MAX_AGE_SECONDS} ]]; then
  send_alert "La dernière sauvegarde date de ${AGE_HOURS} heures (seuil dépassé : ${MAX_AGE_HOURS}h). Sauvegarde obsolète."
  exit 1
fi

# 4. Contrôle d'intégrité non destructif (pg_restore --list)
echo "Vérification de l'intégrité binaire (pg_restore --list)..."
if command -v pg_restore >/dev/null 2>&1; then
  if ! pg_restore --list "${LATEST_DUMP}" >/dev/null 2>&1; then
    send_alert "Corruption détectée ! L'archive '${LATEST_DUMP}' a échoué au contrôle 'pg_restore --list'."
    exit 1
  fi
  echo "✓ Contrôle pg_restore réussi (en-têtes et catalogue d'archives valides)."
else
  echo "ℹ Avertissement : 'pg_restore' non disponible sur la machine locale, vérification binaire basique."
  if [[ ! -s "${LATEST_DUMP}" ]]; then
    send_alert "L'archive '${LATEST_DUMP}' est vide (0 octet)."
    exit 1
  fi
fi

# 5. Écriture du fichier d'état pour FastAPI et des métriques Prometheus
mkdir -p "${BACKUP_DIR}" 2>/dev/null || true
cat <<EOF > "${STATE_FILE}"
{
  "checked_at": ${NOW},
  "is_valid": true,
  "latest_file": "${LATEST_DUMP}",
  "size_mb": ${FILE_SIZE_MB},
  "last_backup_timestamp": ${FILE_MTIME},
  "age_seconds": ${AGE_SECONDS},
  "age_hours": ${AGE_HOURS}
}
EOF

if [[ -d "${PROMETHEUS_TEXTFILE_DIR}" ]]; then
  cat <<EOF > "${PROMETHEUS_TEXTFILE_DIR}/medizy_backup_freshness.prom.$$"
# HELP medizy_last_backup_timestamp Timestamp Unix de la dernière sauvegarde PostGIS certifiée valide
# TYPE medizy_last_backup_timestamp gauge
medizy_last_backup_timestamp ${FILE_MTIME}
# HELP medizy_backup_success_status Statut de conformité de la sauvegarde (1 = conforme, 0 = alerte)
# TYPE medizy_backup_success_status gauge
medizy_backup_success_status 1
# HELP medizy_backup_age_seconds Âge en secondes de la dernière sauvegarde certifiée
# TYPE medizy_backup_age_seconds gauge
medizy_backup_age_seconds ${AGE_SECONDS}
EOF
  mv "${PROMETHEUS_TEXTFILE_DIR}/medizy_backup_freshness.prom.$$" "${PROMETHEUS_TEXTFILE_DIR}/medizy_backup_freshness.prom"
fi

echo "=============================================================================="
echo "✓ SUCCÈS : Sauvegarde conforme, récente (${AGE_HOURS}h < ${MAX_AGE_HOURS}h) et intègre."
echo "=============================================================================="
exit 0
