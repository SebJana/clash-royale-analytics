#!/usr/bin/env bash
set -euo pipefail

DUMP_DIR="${1:-}"
if [[ -z "$DUMP_DIR" || ! -d "$DUMP_DIR" ]]; then
  echo "Usage: $0 ./backups/clash_royale_YYYY-MM-DD_HH-MM-SS"
  exit 1
fi

if [[ -f "../.env" ]]; then
  export $(grep -v '^#' ../.env | xargs)
fi

MONGO_HOST="$MONGO_HOST"
MONGO_PORT="$MONGO_PORT"
MONGO_DB="$MONGO_APP_DB"
MONGO_USER="$MONGO_APP_USER"
MONGO_PWD="$MONGO_APP_PWD"
MONGO_AUTH_DB="$MONGO_APP_DB"

echo "[restore] restoring ${DUMP_DIR} -> ${MONGO_DB} on ${MONGO_HOST}:${MONGO_PORT}"

docker run --rm \
  --network "clash-royale-analytics_cr-analytics" \
  -v "$(realpath "$DUMP_DIR")":/dump:ro \
  mongo:7.0 mongorestore \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PWD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --nsInclude="${MONGO_DB}.*" \
    --drop \
    /dump

echo "[restore] done."
