#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Binance KYC Bot — One-click start script
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# ── Colours ───────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Banner ────────────────────────────────────────────────────
echo -e "${CYAN}"
cat << 'BANNER'
  ╔══════════════════════════════════════════════╗
  ║        Binance KYC Telegram Bot              ║
  ║        Conversational ID Verification        ║
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

if [ -z "$PYTHON" ]; then
    error "Python 3.11+ is required but not found. Please install Python first."
fi

PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$($PYTHON -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$($PYTHON -c 'import sys; print(sys.version_info.minor)')

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    error "Python 3.11+ is required. Found: Python $PY_VERSION"
fi

ok "Python $PY_VERSION found ($PYTHON)"

# ── Virtual environment ───────────────────────────────────────
VENV_DIR="$PROJECT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
    ok "Virtual environment created at $VENV_DIR"
fi

# Activate
source "$VENV_DIR/bin/activate"
ok "Virtual environment activated"

# ── Install dependencies ──────────────────────────────────────
info "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"
ok "Dependencies installed"

# ── Load .env ─────────────────────────────────────────────────
ENV_FILE="$PROJECT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    warn ".env file not found. Creating from template..."
    cp "$PROJECT_DIR/.env.example" "$ENV_FILE" 2>/dev/null || cat > "$ENV_FILE" << 'ENVEOF'
# Binance KYC Bot Configuration
# Copy this file to .env and fill in your values

# Required: Telegram bot token from @BotFather
BINANCE_KYC_TELEGRAM_TOKEN=

# Run mode: demo (default) or production
BINANCE_KYC_MODE=demo

# Logging level: DEBUG, INFO, WARNING, ERROR
BINANCE_KYC_LOG_LEVEL=INFO

# Data storage directory
BINANCE_KYC_DATA_DIR=data

# Production only — Binance API credentials
# BINANCE_KYC_API_KEY=
# BINANCE_KYC_API_SECRET=
ENVEOF
    warn "Please edit .env and set BINANCE_KYC_TELEGRAM_TOKEN"
    warn "Then run this script again."
    exit 0
fi

# Source .env for validation
set -a
source "$ENV_FILE"
set +a

# ── Validate config ──────────────────────────────────────────
if [ -z "${BINANCE_KYC_TELEGRAM_TOKEN:-}" ]; then
    error "BINANCE_KYC_TELEGRAM_TOKEN is not set in .env"
fi

ok "Configuration loaded (mode: ${BINANCE_KYC_MODE:-demo})"

# ── Create data dirs ─────────────────────────────────────────
DATA_DIR="${BINANCE_KYC_DATA_DIR:-data}"
mkdir -p "$DATA_DIR/sessions" "$DATA_DIR/uploads"
ok "Data directories ready"

# ── Run ──────────────────────────────────────────────────────
info "Starting Binance KYC Bot..."
echo ""
exec binance-kyc run
