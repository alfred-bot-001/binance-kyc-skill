#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Run linting, type-checking, and tests
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[RUN]${NC}  $*"; }
ok()    { echo -e "${GREEN}[PASS]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }

EXIT_CODE=0

# ── Ruff (lint + format check) ───────────────────────────────
info "ruff check src/ tests/"
if ruff check src/ tests/; then
    ok "ruff check"
else
    fail "ruff check"
    EXIT_CODE=1
fi

info "ruff format --check src/ tests/"
if ruff format --check src/ tests/; then
    ok "ruff format"
else
    fail "ruff format"
    EXIT_CODE=1
fi

# ── Mypy ──────────────────────────────────────────────────────
info "mypy src/"
if mypy src/; then
    ok "mypy"
else
    fail "mypy"
    EXIT_CODE=1
fi

# ── Pytest ────────────────────────────────────────────────────
info "pytest tests/"
if pytest tests/; then
    ok "pytest"
else
    fail "pytest"
    EXIT_CODE=1
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All checks passed ✅${NC}"
else
    echo -e "${RED}Some checks failed ❌${NC}"
fi

exit $EXIT_CODE
