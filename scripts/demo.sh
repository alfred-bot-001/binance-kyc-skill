#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Binance KYC Demo — One-click start (web interactive demo)
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo -e "${CYAN}"
cat << 'BANNER'
  ╔══════════════════════════════════════════════╗
  ║     Binance KYC — Interactive Web Demo       ║
  ║     Chat-based Identity Verification         ║
  ╚══════════════════════════════════════════════╝
BANNER
echo -e "${NC}"

# ── Python check ──────────────────────────────────────────────
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
[ -z "$PYTHON" ] && error "Python 3.11+ is required"
ok "Python found ($PYTHON)"

# ── Virtual environment ───────────────────────────────────────
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"
ok "Virtual environment activated"

# ── Install dependencies ──────────────────────────────────────
info "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -e .
pip install --quiet fastapi uvicorn
ok "Dependencies installed"

# ── Run demo server ───────────────────────────────────────────
PORT="${PORT:-8099}"
info "Starting demo server..."
echo ""
echo -e "  ${GREEN}🌐 Open in browser:${NC}"
echo -e "  ${CYAN}   http://localhost:${PORT}${NC}         — 💬 Chat Demo"
echo -e "  ${CYAN}   http://localhost:${PORT}/business${NC} — 💼 Business Analysis"
echo ""
exec python -m uvicorn demo_server.app:app --host 0.0.0.0 --port "$PORT" --reload
