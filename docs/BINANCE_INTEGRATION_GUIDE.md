# Binance Engineer Integration Guide

> What Binance needs to provide to take the Chat KYC Skill from demo to production.

---

## TL;DR

**Binance provides 4 things: KYC API endpoints, Liveness page URL, Webhook callbacks, API credentials.**
Everything else is handled by the Skill (AI assistant side).

---

## Architecture

```
User's AI Assistant (Telegram / WhatsApp / Web / any platform)
  │
  ├── binance-kyc skill (installed in assistant)
  │     │
  │     ├── Conversational data collection (name/DOB/nationality/address/ID)
  │     ├── Calls Binance API to submit data
  │     ├── Sends Liveness URL to user
  │     └── Waits for Webhook callback → notifies user of result
  │
  ↕ HTTPS
  │
  Binance KYC Backend (you provide this)
    ├── KYC REST API
    ├── Liveness page (existing capability)
    └── Webhook notifications
```

### Key Insight

The Skill acts as a **chat-native frontend** to Binance's existing KYC backend. No SDK, no WebView, no app integration — just API calls from the user's AI assistant.

---

## What Binance Needs to Provide

### 1. KYC REST API Endpoints

The Skill needs to call 6 endpoints (existing or new):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sapi/v1/kyc/session` | POST | Create KYC session, return session_id |
| `/sapi/v1/kyc/personal-info` | POST | Submit personal info (name, DOB, nationality, address) |
| `/sapi/v1/kyc/document/upload` | POST | Upload ID document photos (multipart/form-data) |
| `/sapi/v1/kyc/liveness/create` | POST | Generate liveness verification page URL |
| `/sapi/v1/kyc/submit` | POST | Final submission for review |
| `/sapi/v1/kyc/status/{session_id}` | GET | Query verification result |

**Example — Create Session:**
```json
POST /sapi/v1/kyc/session
{
  "user_id": "binance_uid_12345",
  "source": "chat_skill",
  "language": "zh"
}

Response:
{
  "session_id": "KYC-20260306-A1B2C3",
  "expires_at": "2026-03-06T10:00:00Z"
}
```

**Example — Submit Personal Info:**
```json
POST /sapi/v1/kyc/personal-info
{
  "session_id": "KYC-20260306-A1B2C3",
  "full_name": "Zhang San",
  "date_of_birth": "1990-05-15",
  "nationality": "CN",
  "address": "88 Jianguo Rd, Chaoyang, Beijing, 100022"
}
```

**Example — Upload Document:**
```
POST /sapi/v1/kyc/document/upload
Content-Type: multipart/form-data

session_id: KYC-20260306-A1B2C3
doc_type: national_id
side: front
file: [binary image data]
```

**Example — Get Liveness URL:**
```json
POST /sapi/v1/kyc/liveness/create
{
  "session_id": "KYC-20260306-A1B2C3"
}

Response:
{
  "liveness_url": "https://kyc.binance.com/liveness?session=xxx&token=xxx",
  "expires_in": 600
}
```

> If Binance already has similar endpoints, just share the API docs / Swagger — the Skill will adapt to your schema.

---

### 2. Liveness Detection Page

**This is an existing Binance capability — no new development needed.**

How the Skill uses it:
1. Calls API to get a tokenized liveness URL
2. Sends the link to the user in chat
3. User opens it in mobile browser → completes face verification on Binance's page
4. Binance sends webhook callback with the result

**Requirements:**
- URL must work in mobile browsers (no Binance App dependency)
- Recommended expiry: 10 minutes
- Support up to 3 retry attempts

---

### 3. Webhook Callbacks

Binance sends POST requests to the Skill's registered webhook URL when:

**Event A — Liveness Completed:**
```json
POST {webhook_base}/kyc/liveness
{
  "session_id": "KYC-20260306-A1B2C3",
  "event": "liveness_completed",
  "result": "passed",
  "timestamp": "2026-03-06T09:06:30Z"
}
```

**Event B — Verification Completed:**
```json
POST {webhook_base}/kyc/result
{
  "session_id": "KYC-20260306-A1B2C3",
  "event": "verification_completed",
  "result": "approved",
  "reason": null,
  "timestamp": "2026-03-06T12:00:00Z"
}
```

When a webhook fires, the Skill will:
1. Look up the user's session
2. Update the KYC state
3. Send a proactive message to the user ("Your KYC is approved!")

---

### 4. API Credentials

The Skill needs credentials to authenticate API calls:

- **Option A:** API Key + Secret (HMAC signature) — standard Binance auth
- **Option B:** OAuth2 Client Credentials
- **Option C:** Internal service-to-service auth

Skill configuration:
```env
BINANCE_KYC_API_KEY=xxx
BINANCE_KYC_API_SECRET=xxx
BINANCE_KYC_API_BASE=https://api.binance.com
BINANCE_KYC_WEBHOOK_BASE=https://skill.example.com/webhook
```

---

## What Binance Does NOT Need to Do

| Item | Who Handles It |
|------|---------------|
| Chat UI / Frontend | Skill (all in-chat) |
| Multi-language support | Skill (7+ languages built-in) |
| Conversational flow / UX | Skill state machine |
| Input validation | Skill validates before submitting |
| Retry / error guidance | Skill handles |
| Multi-platform support | Skill (Telegram, WhatsApp, Web, etc.) |
| SDK / WebView integration | Not needed at all |
| App modifications | Not needed at all |

**Bottom line: Binance provides the backend API. The Skill IS the frontend.**

---

## Integration Timeline

| Phase | Duration |
|-------|----------|
| Binance provides API documentation | 1-2 days |
| Skill adapts to API + staging integration | 3-5 days |
| Integration testing (happy path + edge cases) | 2-3 days |
| Internal beta / canary rollout | 1 week |
| Production launch | — |
| **Total** | **2-3 weeks** |

---

## Security & Compliance

- **Sensitive operations (liveness, final review) stay on Binance side.** The Skill is just a data collection and delivery pipeline.
- **Document photos** are transmitted via encrypted HTTPS directly to Binance API. Not stored long-term on the Skill side.
- **Session data** (personal info) is encrypted at rest and auto-deleted after verification completes.
- **GDPR/CCPA:** User can say "cancel" at any point → session data is immediately purged.
- **Audit trail:** Full conversation logs available for compliance review.

---

## FAQ

**Q: Does this conflict with the existing KYC system?**
A: No. This is just a new frontend entry point (chat). The backend still uses Binance's existing KYC review pipeline.

**Q: Do we need to modify the Binance App?**
A: No. This is completely independent of the app.

**Q: What if the user abandons mid-flow?**
A: The Skill has a 30-minute session timeout. Users can also resume later — the session picks up where they left off.

**Q: How does this handle different countries' requirements?**
A: The Skill supports 25+ countries and adapts the document requirements based on nationality. Country-specific rules can be configured via the API response.

**Q: What about fraud / deepfakes?**
A: Liveness detection is handled entirely by Binance's existing system. The Skill doesn't interfere with or bypass any security checks.

---

## Links

- **Live Demo:** https://alfred-bot-001.github.io/binance-kyc-skill/user-demo.html
- **GitHub:** https://github.com/alfred-bot-001/binance-kyc-skill
- **Skill Definition:** [SKILL.md](../SKILL.md)
