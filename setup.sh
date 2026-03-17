#!/usr/bin/env bash
# setup.sh — One-shot installer for Daily Global Brief (Linux / macOS)
# Usage: bash setup.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="${PYTHON:-python3}"

echo "=== Daily Global Brief Setup ==="
echo "Project directory: $PROJECT_DIR"

# ── 1. Check Python ───────────────────────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
    echo "ERROR: python3 not found. Install it with: sudo apt install python3 python3-venv"
    exit 1
fi
PY_VERSION=$("$PYTHON" --version 2>&1)
echo "Python: $PY_VERSION"

# ── 2. Create virtualenv ──────────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in .venv …"
    "$PYTHON" -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# ── 3. Install dependencies ───────────────────────────────────────────────────
echo "Installing dependencies…"
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" --quiet
echo "Dependencies installed."

# ── 4. Create .env from .env.example if missing ───────────────────────────────
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo ""
    echo "Created .env from .env.example"
    echo ">>> Please edit .env and fill in your API keys before running. <<<"
else
    echo ".env already exists — skipping."
fi

# ── 5. Create logs directory ──────────────────────────────────────────────────
mkdir -p "$PROJECT_DIR/logs"
echo "Logs directory ready."

# ── 6. Print cron snippet ─────────────────────────────────────────────────────
PYTHON_BIN="$VENV_DIR/bin/python"
MAIN_SCRIPT="$PROJECT_DIR/main.py"
LOG_FILE="$PROJECT_DIR/logs/cron.log"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys (ANTHROPIC_API_KEY, Twilio credentials, phone numbers)"
echo "  2. Test a dry run:  $PYTHON_BIN $MAIN_SCRIPT --dry-run"
echo "  3. Add this line to your crontab (run: crontab -e):"
echo ""
echo "  0 8 * * * cd $PROJECT_DIR && $PYTHON_BIN $MAIN_SCRIPT >> $LOG_FILE 2>&1"
echo ""
