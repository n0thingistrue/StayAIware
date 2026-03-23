#!/usr/bin/env bash
# setup_openclaw.sh — Start OpenClaw on the VPS.
# Run from the project root: bash deploy/setup_openclaw.sh
#
# Modes:
#   bash deploy/setup_openclaw.sh            # start container
#   bash deploy/setup_openclaw.sh --restart  # stop + restart
#   bash deploy/setup_openclaw.sh --logs     # follow container logs
#   bash deploy/setup_openclaw.sh --link     # link WhatsApp account (QR in terminal)

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_DIR}/deploy/docker-compose.yml"
ENV_FILE="${PROJECT_DIR}/.env"
CONTAINER_NAME="openclaw"

info() { echo "[INFO]  $*"; }
die()  { echo "[ERROR] $*" >&2; exit 1; }

command -v docker &>/dev/null || die "Docker not found. Run: apt install docker.io -y"
[ -f "${ENV_FILE}" ]     || die ".env not found at ${ENV_FILE}"
[ -f "${COMPOSE_FILE}" ] || die "docker-compose.yml not found at ${COMPOSE_FILE}"

# Detect docker compose command (plugin vs standalone)
if docker compose version &>/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    info "docker compose not found — installing docker-compose…"
    apt install -y docker-compose || die "Failed to install docker-compose. Run: apt install docker-compose -y"
    COMPOSE="docker-compose"
fi

if [[ "${1:-}" == "--logs" ]]; then
    exec docker logs -f "${CONTAINER_NAME}"
fi

if [[ "${1:-}" == "--restart" ]]; then
    info "Stopping container…"
    if [[ "${COMPOSE}" == "docker compose" ]]; then
        $COMPOSE -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" down
    else
        $COMPOSE -f "${COMPOSE_FILE}" down
    fi
fi

if [[ "${1:-}" == "--link" ]]; then
    info "Enabling WhatsApp plugin…"
    docker exec "${CONTAINER_NAME}" openclaw plugins enable whatsapp
    info "Restarting gateway to apply plugin…"
    docker restart "${CONTAINER_NAME}"
    sleep 15
    info "Starting WhatsApp login — scan the QR code with your phone:"
    docker exec -it "${CONTAINER_NAME}" openclaw channels login --channel whatsapp
    exit 0
fi

chmod 600 "${ENV_FILE}"
info ".env permissions set to 600."

info "Pulling image and starting OpenClaw…"
if [[ "${COMPOSE}" == "docker compose" ]]; then
    $COMPOSE -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --pull always
else
    $COMPOSE -f "${COMPOSE_FILE}" up -d
fi

info "Fixing volume permissions…"
docker run --rm -v openclaw_config:/data alpine chown -R 1000:1000 /data
docker run --rm -v openclaw_workspace:/data alpine chown -R 1000:1000 /data

info "Waiting for container to be healthy (up to 90s)…"
for i in $(seq 1 18); do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "starting")
    if [[ "${STATUS}" == "healthy" ]]; then
        info "Container is healthy."
        break
    fi
    echo -n "  [${i}/18] ${STATUS}…"
    sleep 5
done
echo ""

WHATSAPP_TO=$(grep WHATSAPP_TO_NUMBER "${ENV_FILE}" | cut -d= -f2 | tr -d '"' | sed 's/whatsapp://')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NEXT STEP — Link your WhatsApp account"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Run this to scan the QR code directly in your terminal:"
echo "    bash deploy/setup_openclaw.sh --link"
echo ""
echo "  Then test:"
echo "    docker exec ${CONTAINER_NAME} \\"
echo "      openclaw message send --channel whatsapp \\"
echo "      --target ${WHATSAPP_TO} --message 'Test OK'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
docker ps --filter name="${CONTAINER_NAME}" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ""
