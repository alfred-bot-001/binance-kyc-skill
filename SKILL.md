---
name: binance-kyc
description: "Binance KYC identity verification skill. Install this skill to let your AI assistant guide you through Binance's KYC process — collect personal info, upload ID documents, and complete liveness verification. Triggers on: 'KYC', 'verify identity', 'binance verification', '身份验证', '实名认证'."
metadata:
  author: "Binance KYC Team"
  version: "0.2.0"
  homepage: "https://github.com/alfred-bot-001/binance-kyc-skill"
---

# Binance KYC Skill

**Let your users complete Binance identity verification through natural conversation with their own AI assistant.**

This is NOT a standalone bot. It's an OpenClaw skill that any agent can install — the user's own assistant becomes the KYC guide.

## How It Works

```
┌──────────────────────────────────────────────────────────────┐
│  User's AI Assistant (OpenClaw)                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  binance-kyc skill (installed)                          │ │
│  │                                                         │ │
│  │  Chat Flow:  Info → Docs → Review → Liveness → Done    │ │
│  │                                        ↓                │ │
│  │                              Binance Liveness URL       │ │
│  │                              (user opens in browser)    │ │
│  │                                        ↓                │ │
│  │                              Webhook callback           │ │
│  │                              (liveness result)          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                         ↕ Binance KYC API                    │
│                   ┌─────────────┐                            │
│                   │ Binance     │                            │
│                   │ KYC Backend │                            │
│                   └─────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

## When to Trigger

Activate this skill when the user says any of:
- "Start KYC", "verify my identity", "binance verification"
- "开始KYC", "实名认证", "身份验证"
- "KYC", "verify", "验证"
- Or when the user's Binance account requires KYC completion

## Complete Flow

### Phase 1: Conversational Data Collection (in chat)

```
User: "I need to verify my Binance account"
Agent: "I can help with that! Let's start your identity verification.
        This takes about 3 minutes. You'll need your ID document ready.
        Shall we begin?"

User: "Yes"
Agent: "What's your full legal name (as shown on your ID)?"

User: "Zhang San"
Agent: "Date of birth? (YYYY-MM-DD)"

User: "1990-05-15"
Agent: "Nationality?"

User: "China"
Agent: "Residential address? (street, city, postal code, country)"

User: "北京市朝阳区建国路88号, 100022"
Agent: "Which ID document will you use?
        1️⃣ Passport
        2️⃣ National ID Card
        3️⃣ Driver's License"

User: "2"
Agent: "Please send a clear photo of the FRONT of your National ID Card.
        Tips: ✅ Flat surface ✅ Good lighting ✅ All corners visible"

User: [sends photo]
Agent: "Now the BACK of your ID card."

User: [sends photo]
Agent: "Let me confirm your information:
        👤 Zhang San
        📅 1990-05-15
        🌍 China
        📍 北京市朝阳区建国路88号, 100022
        📄 National ID Card ✅
        Is everything correct? (Confirm / Edit)"

User: "Confirm"
```

### Phase 2: Liveness Check (browser redirect)

```
Agent: "Almost done! For security, we need a quick face verification.
        Please open this link to complete the liveness check:

        🔗 https://kyc.binance.com/liveness?session=KYC-20260306-A1B2C3&token=xxx

        This will open Binance's secure video verification page.
        It takes about 30 seconds — just follow the on-screen instructions.

        I'll wait here. Let me know when you're done, or I'll get notified automatically! ⏳"

[User opens link in browser → Binance liveness page → face scan → done]

[Webhook callback hits the agent: liveness_passed=true]

Agent: "✅ Liveness check passed!

        Your verification has been submitted.
        📋 Reference: KYC-20260306-A1B2C3

        ⏳ Processing usually takes 1-3 business days.
        I'll notify you as soon as it's complete!"

[Later, async webhook:]

Agent: "🎉 Great news! Your Binance identity verification is approved!
        You now have full access to Binance services."
```

## State Machine

```
awaiting_consent
       ↓
collecting_name → collecting_dob → collecting_nationality → collecting_address
       ↓
selecting_document → uploading_doc_front → [uploading_doc_back] → reviewing
       ↓
awaiting_liveness  ← USER OPENS BROWSER LINK
       ↓ (webhook callback)
submitted → approved / rejected
```

### States

| State | Input | Agent Action |
|-------|-------|-------------|
| `awaiting_consent` | "yes" / "no" | Explain process, get agreement |
| `collecting_name` | text | Validate name (2-100 chars) |
| `collecting_dob` | date | Validate 18+ age |
| `collecting_nationality` | text | Match to supported countries |
| `collecting_address` | text | Validate length (10-500 chars) |
| `selecting_document` | "1"/"2"/"3" | Set document type |
| `uploading_doc_front` | image | Save, validate quality |
| `uploading_doc_back` | image | Save (skip for passport) |
| `reviewing` | "confirm"/"edit" | Show summary, get confirmation |
| `awaiting_liveness` | — (webhook) | Send liveness URL, wait for callback |
| `submitted` | — (webhook) | Verification in progress |
| `approved` | — | Notify user of success |
| `rejected` | — | Notify user, offer retry |

## Agent Behavior Guidelines

### Tone
- Be helpful and efficient, not corporate
- Match the user's language (auto-detect from their messages)
- Don't repeat the full flow explanation at every step
- Be concise: "What's your full name?" not "Please provide your full legal name as it appears on your government-issued identification document"

### Error Handling
- Invalid input → explain what's expected, ask again (don't restart)
- Blurry photo → "That's a bit unclear. Try better lighting?"
- Unsupported country → "Sorry, [country] isn't supported yet. Supported: ..."
- User says "cancel" at any point → cancel and delete session data
- Timeout (30 min inactivity) → "Still there? Your KYC session is still active."

### Liveness Check
- The liveness URL is a Binance-hosted page, NOT something we build
- Send the URL as a clickable link in chat
- The URL contains a session token — expires in 10 minutes
- After user completes liveness, we receive a webhook callback
- If no callback in 10 min, prompt user: "Did you complete the face scan? Here's the link again: ..."
- Retry limit: 3 attempts for liveness

### Multi-language
- Detect language from user's first message
- Supported: en, zh, ja, ko, es, pt, ru
- All agent messages should be in the detected language
- Don't switch languages mid-conversation unless user does

## Session Storage

Sessions are stored per user as JSON in the agent's workspace:

```
workspace/kyc-sessions/<user_id>.json
```

```json
{
  "session_id": "KYC-20260306-A1B2C3",
  "user_id": "telegram_12345",
  "state": "awaiting_liveness",
  "language": "zh",
  "created_at": "2026-03-06T09:00:00Z",
  "updated_at": "2026-03-06T09:05:00Z",
  "personal_info": {
    "full_name": "Zhang San",
    "date_of_birth": "1990-05-15",
    "nationality": "China",
    "address": "北京市朝阳区建国路88号, 100022"
  },
  "document": {
    "type": "national_id",
    "front_image": "uploads/doc_front_12345.jpg",
    "back_image": "uploads/doc_back_12345.jpg"
  },
  "liveness": {
    "url": "https://kyc.binance.com/liveness?session=...",
    "status": "pending",
    "attempts": 1,
    "expires_at": "2026-03-06T09:15:00Z"
  },
  "verification": {
    "status": "pending",
    "submitted_at": null,
    "result": null
  }
}
```

## API Integration

### Binance KYC API (production)

The skill calls these Binance API endpoints:

```
POST /sapi/v1/kyc/session          → Create KYC session, get session_id
POST /sapi/v1/kyc/personal-info    → Submit personal info
POST /sapi/v1/kyc/document/upload  → Upload ID document images
POST /sapi/v1/kyc/liveness/create  → Get liveness check URL
GET  /sapi/v1/kyc/liveness/status  → Poll liveness result
POST /sapi/v1/kyc/submit           → Final submission
GET  /sapi/v1/kyc/status/{id}      → Check verification result
```

### Webhook Callbacks

The skill registers webhook endpoints for async notifications:

```
POST /webhook/kyc/liveness   → Liveness check completed
POST /webhook/kyc/result     → Verification approved/rejected
```

When a webhook fires, the skill should:
1. Load the user's session
2. Update the state
3. Send a proactive message to the user via their agent

### Configuration

The installing user's agent needs these env vars (or the skill prompts for them):

```
BINANCE_KYC_API_KEY=xxx          # Binance API key
BINANCE_KYC_API_SECRET=xxx       # Binance API secret
BINANCE_KYC_WEBHOOK_BASE=https://...  # Webhook callback URL
```

In **demo mode** (no API keys configured):
- All API calls are simulated
- Liveness URL points to a demo page
- Auto-approves after 10 seconds
- No real data leaves the agent

## Validation Rules

| Field | Rule |
|-------|------|
| Name | 2-100 chars, not all symbols |
| DOB | Valid date, age ≥ 18 |
| Nationality | Must be in supported countries list |
| Address | 10-500 chars |
| Document images | JPG/PNG, 100KB-10MB |
| Liveness | Max 3 attempts, URL expires in 10 min |

## Supported Countries

Argentina, Australia, Brazil, Canada, China, France, Germany, Hong Kong,
India, Indonesia, Japan, Mexico, Netherlands, Philippines, Russia,
Saudi Arabia, Singapore, South Korea, Switzerland, Turkey, UAE, Ukraine,
United Kingdom, United States, Vietnam

## File Structure

```
skills/binance-kyc/
├── SKILL.md                     # This file (agent instructions)
├── src/binance_kyc/             # Core Python package
│   ├── models/                  # Pydantic data models
│   ├── services/                # State machine, validators, API client
│   ├── handlers/                # Telegram handler (optional)
│   └── messages/                # Multi-language templates (en.json, zh.json)
├── demo_server/                 # Interactive web demo
├── static/                      # Demo frontend
├── tests/                       # 76+ unit tests
├── scripts/
│   ├── demo.sh                  # Start web demo
│   └── start.sh                 # Start Telegram bot (standalone mode)
└── pyproject.toml               # Python project config
```
