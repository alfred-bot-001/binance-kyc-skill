# Binance KYC Telegram Bot

> Conversational identity verification via Telegram — complete KYC without leaving the chat.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

[中文文档](README_ZH.md)

---

## ✨ Features

- **Conversational Flow** — step-by-step identity verification through natural chat
- **12-State Machine** — robust state management with full flow control
- **Multi-language** — English, Chinese (extensible to any language)
- **Input Validation** — name, DOB (18+), nationality, address, document images
- **Multiple ID Types** — passport, national ID card, driver's license
- **Demo Mode** — runs without real API calls for development and testing
- **Persistent Sessions** — per-user state saved as JSON, survives restarts
- **Docker Ready** — one-command deployment with Docker Compose

## 🌐 Interactive Web Demo

Try the full KYC flow in your browser — no Telegram required:

```bash
./scripts/demo.sh
```

Open:
- **http://localhost:8099** — 💬 Chat Demo (simulated Telegram conversation)
- **http://localhost:8099/business** — 💼 Business Analysis (market data, ROI calculator, competitive analysis)

The demo includes:
- Real-time chat interface mimicking Telegram
- Step-by-step progress tracking
- Side-by-side comparison with traditional KYC
- Interactive ROI calculator
- Full competitive analysis (Jumio, Onfido, Sumsub)

## 📋 Architecture

```
User (Telegram) ←→ python-telegram-bot ←→ State Machine ←→ Session Store (JSON)
                                                ↓
                                    [Production] Binance KYC API
```

### KYC Flow

```
/start_kyc → Consent → Full Name → Date of Birth → Nationality → Address
→ Select Document Type → Upload Front → [Upload Back] → Selfie
→ Review & Confirm → Submitted → Approved ✅
```

### Project Structure

```
binance-kyc-skill/
├── src/binance_kyc/             # Core package
│   ├── __init__.py              # Package metadata
│   ├── cli.py                   # CLI entry point
│   ├── config.py                # Settings (env vars + .env)
│   ├── models/
│   │   ├── enums.py             # KYCState, DocumentType, etc.
│   │   └── session.py           # Pydantic session model
│   ├── services/
│   │   ├── state_machine.py     # State transitions & flow logic
│   │   ├── session_store.py     # JSON file persistence
│   │   └── validators.py        # Input validation
│   ├── handlers/
│   │   └── telegram.py          # Telegram bot handlers
│   ├── messages/
│   │   ├── __init__.py          # Message loader + language detection
│   │   ├── en.json              # English templates
│   │   └── zh.json              # Chinese templates
│   └── utils/
│       └── logging.py           # Structured logging (structlog)
├── demo_server/                 # Interactive web demo
│   └── app.py                   # FastAPI demo server
├── static/                      # Web demo frontend
│   ├── index.html               # Chat demo page
│   ├── business.html            # Business analysis page
│   ├── style.css                # Dark theme UI
│   ├── app.js                   # Chat demo logic
│   └── i18n.js                  # EN/ZH language toggle
├── tests/                       # pytest test suite (76 tests)
├── scripts/
│   ├── start.sh                 # One-click Telegram bot start
│   ├── demo.sh                  # One-click web demo start
│   └── lint.sh                  # Lint + type-check + test
├── pyproject.toml               # PEP 621 project config
├── Dockerfile                   # Container image
├── docker-compose.yml           # One-command deployment
├── .env.example                 # Configuration template
├── SKILL.md                     # OpenClaw skill definition
└── LICENSE                      # MIT License
```

## 🚀 Quick Start

### Option 1: One-Click Script

```bash
git clone https://github.com/alfred-bot-001/binance-kyc-skill.git
cd binance-kyc-skill

# First run creates .env — edit it with your Telegram token
./scripts/start.sh

# Edit .env, then run again
./scripts/start.sh
```

### Option 2: Manual Setup

```bash
# Clone
git clone https://github.com/alfred-bot-001/binance-kyc-skill.git
cd binance-kyc-skill

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env — set BINANCE_KYC_TELEGRAM_TOKEN

# Run
binance-kyc run
```

### Option 3: Docker

```bash
cp .env.example .env
# Edit .env — set BINANCE_KYC_TELEGRAM_TOKEN

docker compose up -d
```

## ⚙️ Configuration

All settings are controlled via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `BINANCE_KYC_TELEGRAM_TOKEN` | *(required)* | Telegram bot token from @BotFather |
| `BINANCE_KYC_MODE` | `demo` | `demo` or `production` |
| `BINANCE_KYC_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `BINANCE_KYC_DEFAULT_LANGUAGE` | `en` | Default language code |
| `BINANCE_KYC_DATA_DIR` | `data` | Session & upload storage path |
| `BINANCE_KYC_SESSION_TIMEOUT_MINUTES` | `30` | Inactivity timeout |
| `BINANCE_KYC_API_KEY` | — | Binance API key (production only) |
| `BINANCE_KYC_API_SECRET` | — | Binance API secret (production only) |

## 🤖 Telegram Bot Setup

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot: `/newbot`
3. Copy the token to your `.env` file
4. Register commands with BotFather:

```
start_kyc - Start identity verification
status - Check verification status
cancel - Cancel current verification
help - Show help message
```

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Type checking
mypy src/

# Format code
ruff format src/ tests/

# All checks at once
./scripts/lint.sh
```

## 🌍 Adding a Language

1. Create `src/binance_kyc/messages/<lang_code>.json` based on `en.json`
2. Translate all message strings
3. (Optional) Add detection patterns to `messages/__init__.py`

## 📦 Demo Mode vs Production

### Demo Mode (default)
- No real API calls
- Verification auto-approves after 10 seconds
- Images saved locally, not transmitted
- Perfect for development and demos

### Production Mode
Set `BINANCE_KYC_MODE=production` and provide API credentials. The bot will:
- Submit data to Binance KYC API endpoints
- Perform real document verification
- Return actual approval/rejection results

## 📄 License

[MIT](LICENSE)
