# Binance KYC Skill

Conversational KYC (Know Your Customer) verification flow for Binance, built as an [OpenClaw](https://openclaw.ai) skill. Users complete identity verification entirely through a Telegram bot chat interface.

## Features

- 🔄 **Multi-step state machine** — Welcome → Personal Info → Document Upload → Selfie → Review → Submit
- 🌍 **Multi-language** — English, Chinese (more coming)
- ✅ **Input validation** — Name, DOB (18+), nationality, address, image format/size
- 📄 **Multiple ID types** — Passport, National ID, Driver's License
- 🔒 **Demo mode** — Runs without real API calls for testing
- 💾 **Session persistence** — Per-user state saved as JSON

## Flow

```
/start_kyc → Consent → Name → DOB → Nationality → Address
→ Select Doc Type → Upload Front → [Upload Back] → Selfie
→ Review & Confirm → Submitted ✅
```

## Quick Start

### As an OpenClaw Skill

1. Copy the `binance-kyc` folder into your OpenClaw `skills/` directory
2. The agent will automatically pick it up when users mention KYC
3. Connect via Telegram and type `/start_kyc`

### Standalone Test

```bash
python3 kyc_flow.py
```

## File Structure

```
├── SKILL.md          # Skill definition & agent behavior guide
├── kyc_flow.py       # Core state machine & flow controller
├── validators.py     # Input validation (name, DOB, nationality, etc.)
├── messages/
│   ├── en.json       # English message templates
│   └── zh.json       # Chinese message templates
└── README.md         # This file
```

## Production Setup

Set environment variables to connect to real Binance KYC APIs:

```bash
export BINANCE_KYC_MODE=production
export BINANCE_KYC_API_KEY=your_key
export BINANCE_KYC_API_SECRET=your_secret
```

## License

MIT
