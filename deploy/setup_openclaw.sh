#!/usr/bin/env bash
# setup_openclaw.sh — Deploy OpenClaw on a remote VPS
#
# What this script does:
#   1. Connects to the VPS over SSH
#   2. Installs Docker if absent (does NOT touch K3s)
#   3. Creates /opt/openclaw, uploads docker-compose.yml + .env
#   4. Starts the OpenClaw container
#   5. Prints QR-scan instructions for WhatsApp linking
#   6. Opens an SSH tunnel so you can reach the UI locally
#
# Usage:
#   export VPS_HOST=your.vps.ip VPS_USER=root
#   bash setup_openclaw.sh              # full deploy
#   bash setup_openclaw.sh --tunnel     # only open the SSH tunnel

set -euo pipefail

# ── Config — set via environment, no defaults to avoid accidental deploys ─────
VPS_HOST="${VPS_HOST:?Set VPS_HOST before running. e.g. export VPS_HOST=1.2.3.4}"
VPS_USER="${VPS_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/openclaw}"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_PORT="${LOCAL_PORT:-8080}"   # tunnel: localhost:$LOCAL_PORT → VPS:18789
CONTAINER_NAME="openclaw"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
die()   { echo "[ERROR] $*" >&2; exit 1; }

ssh_run() { ssh "${VPS_USER}@${VPS_HOST}" "$@"; }

# ── Tunnel-only mode ──────────────────────────────────────────────────────────
if [[ "${1:-}" == "--tunnel" ]]; then
    info "Opening SSH tunnel: localhost:${LOCAL_PORT} → ${VPS_HOST}:18789"
    info "Open http://localhost:${LOCAL_PORT} in your browser."
    info "Press Ctrl+C to close."
    exec ssh -N -L "${LOCAL_PORT}:127.0.0.1:18789" "${VPS_USER}@${VPS_HOST}"
fi

# ── 1. Verify SSH access ──────────────────────────────────────────────────────
info "Testing SSH connection to ${VPS_USER}@${VPS_HOST}…"
ssh_run "echo 'SSH OK'" || die "Cannot connect. Check your SSH key / VPN."

# ── 2. Install Docker (skip if already present, never touch K3s) ─────────────
info "Checking Docker on VPS…"
if ssh_run "command -v docker &>/dev/null"; then
    DOCKER_VER=$(ssh_run "docker --version")
    info "Docker already installed: ${DOCKER_VER}"
else
    warn "Docker not found — installing via get.docker.com…"
    ssh_run "curl -fsSL https://get.docker.com | sh"
    ssh_run "systemctl enable --now docker"
    info "Docker installed and started."
fi

ssh_run "docker info &>/dev/null" || die "Docker daemon is not running on VPS."

# ── 3. Prepare remote directory ───────────────────────────────────────────────
info "Creating ${REMOTE_DIR} on VPS…"
ssh_run "mkdir -p ${REMOTE_DIR}/logs"

# ── 4. Upload files ───────────────────────────────────────────────────────────
info "Uploading docker-compose.yml…"
scp "${LOCAL_DIR}/docker-compose.yml" "${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}/docker-compose.yml"

info "Uploading .env as openclaw.env (never committed to git)…"
scp "${LOCAL_DIR}/.env" "${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}/openclaw.env"

ssh_run "chmod 600 ${REMOTE_DIR}/openclaw.env"
info ".env permissions set to 600."

# ── 5. Start OpenClaw ─────────────────────────────────────────────────────────
info "Pulling latest OpenClaw image and starting container…"
ssh_run "
    cd ${REMOTE_DIR}
    docker compose --env-file openclaw.env up -d --pull always
"

# Wait for healthy
info "Waiting for OpenClaw to be healthy (up to 90s)…"
for i in $(seq 1 18); do
    STATUS=$(ssh_run "docker inspect --format='{{.State.Health.Status}}' ${CONTAINER_NAME}" 2>/dev/null || echo "starting")
    if [[ "${STATUS}" == "healthy" ]]; then
        info "Container is healthy."; break
    fi
    echo -n "  [${i}/18] status=${STATUS} …"
    sleep 5
done
echo ""

# ── 6. WhatsApp QR scan ───────────────────────────────────────────────────────
WHATSAPP_TO="${WHATSAPP_TO_NUMBER:-your WhatsApp number from .env}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NEXT STEP — Link your WhatsApp account"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1. Open the tunnel in another terminal:"
echo "       VPS_HOST=${VPS_HOST} bash setup_openclaw.sh --tunnel"
echo ""
echo "  2. Open http://localhost:${LOCAL_PORT} in your browser."
echo ""
echo "  3. OpenClaw UI → Channels → WhatsApp → 'Link device'"
echo "     Scan the QR with the WhatsApp app (${WHATSAPP_TO}):"
echo "       WhatsApp → Settings → Linked Devices → Link a Device"
echo ""
echo "  4. QR codes expire in 60s — scan quickly."
echo "     Session is saved in the Docker volume on restart."
echo ""
echo "  5. Test from the VPS:"
echo "       ssh ${VPS_USER}@${VPS_HOST} \\"
echo "         docker exec ${CONTAINER_NAME} \\"
echo "         openclaw message send --channel whatsapp \\"
echo "         --target \${WHATSAPP_TO_NUMBER} --message 'OpenClaw test OK'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 7. Status ─────────────────────────────────────────────────────────────────
echo ""
info "Container status:"
ssh_run "docker ps --filter name=${CONTAINER_NAME} --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo ""
info "Logs (last 20 lines):"
ssh_run "docker logs --tail 20 ${CONTAINER_NAME}" 2>&1 || true
echo ""
info "Setup complete. Cron job to add on the VPS:"
echo ""
echo "  0 8 * * * cd ${REMOTE_DIR} && .venv/bin/python main.py --openclaw >> ${REMOTE_DIR}/logs/cron.log 2>&1"
echo ""
