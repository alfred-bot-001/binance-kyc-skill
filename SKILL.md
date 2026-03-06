---
name: binance-kyc
description: "Binance KYC verification flow via conversational chat. Guides users through identity verification step-by-step: collect personal info, capture/upload ID documents, perform liveness check, and submit for review. Designed for Telegram bot integration."
---

# Binance KYC Skill

Guide users through the complete Binance KYC (Know Your Customer) verification process via conversational chat. Users interact with a Telegram bot to complete identity verification without leaving the chat interface.

## Overview

This skill implements a multi-step KYC flow:

1. **Welcome & Consent** — Explain the process, get user agreement
2. **Personal Information** — Collect name, DOB, nationality, address
3. **Document Selection** — User chooses ID type (passport, national ID, driver's license)
4. **Document Upload** — User sends photos of their ID document (front + back if applicable)
5. **Selfie / Liveness Check** — User sends a selfie for facial matching
6. **Review & Submit** — Confirm all data, submit for verification
7. **Status Updates** — Notify user of verification result

## Flow Diagram

```
┌─────────────┐
│   Start     │
│  /start_kyc │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  1. Welcome &   │
│     Consent     │
│  (T&C, Privacy) │
└──────┬──────────┘
       │ User agrees
       ▼
┌─────────────────┐
│ 2. Personal Info│
│  - Full name    │
│  - Date of birth│
│  - Nationality  │
│  - Address      │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ 3. Select Doc   │
│  - Passport     │
│  - National ID  │
│  - Driver's Lic │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ 4. Upload Docs  │
│  - Front photo  │
│  - Back photo   │
│  (quality check)│
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ 5. Selfie /     │
│    Liveness     │
│  - Take selfie  │
│  - Hold ID next │
│    to face      │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ 6. Review &     │
│    Confirm      │
│  - Show summary │
│  - User confirm │
└──────┬──────────┘
       │
       ▼
┌─────────────────────┐
│ 7. Submit &         │
│    Await Result     │
│  - Processing...    │
│  - Approved ✅      │
│  - Rejected ❌      │
│    (retry option)   │
└─────────────────────┘
```

## State Machine

The KYC session state is tracked per user in `workspace/kyc-sessions/`. Each user gets a JSON file:

```json
{
  "user_id": "telegram_user_id",
  "state": "awaiting_consent",
  "created_at": "2026-03-06T09:00:00Z",
  "updated_at": "2026-03-06T09:05:00Z",
  "personal_info": {
    "full_name": null,
    "date_of_birth": null,
    "nationality": null,
    "address": null
  },
  "document": {
    "type": null,
    "front_image": null,
    "back_image": null
  },
  "selfie": {
    "image": null
  },
  "verification": {
    "status": "pending",
    "submitted_at": null,
    "result": null,
    "rejection_reason": null
  }
}
```

### States

| State | Description | Expected Input |
|-------|-------------|----------------|
| `awaiting_consent` | Show T&C, wait for agreement | "agree" / "yes" |
| `collecting_name` | Ask for full legal name | Text |
| `collecting_dob` | Ask for date of birth | Date (YYYY-MM-DD) |
| `collecting_nationality` | Ask for nationality | Text / country |
| `collecting_address` | Ask for residential address | Text |
| `selecting_document` | Choose document type | "passport" / "id" / "license" |
| `uploading_doc_front` | Upload front of document | Image |
| `uploading_doc_back` | Upload back of document | Image (skip for passport) |
| `uploading_selfie` | Take selfie with ID | Image |
| `reviewing` | Confirm all information | "confirm" / "edit" |
| `submitted` | Verification in progress | — |
| `approved` | KYC passed | — |
| `rejected` | KYC failed, can retry | "retry" |

## Agent Behavior

When a user initiates KYC (says "start KYC", "verify my identity", "开始KYC", etc.):

### Step 1: Welcome
```
👋 Welcome to Binance Identity Verification!

To use Binance services, we need to verify your identity. This process takes about 5 minutes.

You'll need:
📄 A valid government-issued ID (passport, national ID, or driver's license)
📸 A clear selfie
📍 Your current residential address

Your data is encrypted and handled per our Privacy Policy.

Do you agree to proceed? (Yes / No)
```

### Step 2: Personal Information
Collect each field one at a time in a natural conversation:
- **Full legal name** (as shown on your ID)
- **Date of birth** (validate format)
- **Nationality** (validate against supported countries)
- **Residential address** (street, city, postal code, country)

### Step 3: Document Selection
```
Please select your ID document type:

1️⃣ Passport
2️⃣ National ID Card
3️⃣ Driver's License
```

### Step 4: Document Upload
- Request front photo (and back if National ID / Driver's License)
- Validate image quality (not blurry, well-lit, all corners visible)
- If quality is poor, ask to retake

### Step 5: Selfie
- Request a clear selfie
- Optionally: ask user to hold their ID next to their face
- Validate face is visible and matches document photo

### Step 6: Review
Show a summary of all collected info and ask for confirmation:
```
📋 Please review your information:

👤 Name: John Doe
📅 DOB: 1990-01-15
🌍 Nationality: United States
📍 Address: 123 Main St, New York, NY 10001

📄 Document: Passport ✅
📸 Selfie: Uploaded ✅

Is everything correct? (Confirm / Edit)
```

### Step 7: Submit
```
✅ Your verification has been submitted!

⏳ Processing usually takes 1-3 business days.
We'll notify you as soon as your verification is complete.

Your reference ID: KYC-2026-XXXXX
```

## Validation Rules

| Field | Validation |
|-------|-----------|
| Name | 2-100 chars, letters/spaces/hyphens only |
| DOB | Valid date, user must be 18+ |
| Nationality | Must be in supported countries list |
| Address | Non-empty, reasonable length |
| Images | JPG/PNG, 100KB-10MB, min 640x480 resolution |

## Supported Countries (Demo)

For the demo, support these tier-1 markets:
- United States, United Kingdom, Canada, Australia
- Japan, South Korea, Singapore, Hong Kong
- Germany, France, Netherlands, Switzerland
- Brazil, Mexico, Argentina
- India, Indonesia, Philippines, Vietnam
- UAE, Saudi Arabia, Turkey
- Russia, Ukraine

## Error Handling

- **Invalid input** → Explain what's expected, ask again
- **Image too blurry** → "The image appears unclear. Please retake in good lighting."
- **Unsupported country** → "Sorry, verification is not available in your region yet."
- **Session timeout** (30 min no activity) → "Your session expired. Type /start_kyc to begin again."
- **User wants to cancel** → "KYC cancelled. Your data has been deleted. Type /start_kyc to try again."

## Multi-language Support

Detect user's language from their messages and respond accordingly. Support at minimum:
- English (en)
- Chinese Simplified (zh-CN)
- Japanese (ja)
- Korean (ko)
- Spanish (es)
- Portuguese (pt)
- Russian (ru)

## API Integration Points (Production)

In production, these would connect to real Binance APIs:

```
POST /api/v1/kyc/session/create     → Create KYC session
POST /api/v1/kyc/personal-info      → Submit personal info
POST /api/v1/kyc/document/upload    → Upload ID document
POST /api/v1/kyc/selfie/upload      → Upload selfie
POST /api/v1/kyc/submit             → Submit for review
GET  /api/v1/kyc/status/{id}        → Check verification status
```

## Demo Mode

This skill runs in **demo mode** by default:
- No actual API calls to Binance backend
- Document "verification" is simulated (always approves after 10s delay)
- Images are saved locally but not sent anywhere
- All user data stays in the sandbox

To switch to production mode, set environment variable:
```
BINANCE_KYC_MODE=production
BINANCE_KYC_API_KEY=xxx
BINANCE_KYC_API_SECRET=xxx
```

## File Structure

```
skills/binance-kyc/
├── SKILL.md              # This file
├── kyc_flow.py           # Main flow controller
├── validators.py         # Input validation
├── messages/             # Message templates (multi-language)
│   ├── en.json
│   ├── zh.json
│   └── ...
└── README.md             # Developer documentation
```
