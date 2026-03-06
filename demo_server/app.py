"""Binance KYC Demo Server — FastAPI backend for the interactive web demo.

Simulates the full KYC conversation flow with a chat-style interface.
Reuses the core state machine, validators, and messages from the main package.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from binance_kyc.messages import detect_language, get
from binance_kyc.models.enums import (
    DOUBLE_SIDE_DOCUMENTS,
    DocumentType,
    KYCState,
    VerificationStatus,
)
from binance_kyc.models.session import Session
from binance_kyc.services.state_machine import advance, can_retry, next_state, reset_for_retry
from binance_kyc.services.validators import (
    validate_address,
    validate_date_of_birth,
    validate_document_type,
    validate_name,
    validate_nationality,
)

app = FastAPI(title="Binance KYC Demo", description="Interactive KYC verification demo")

# ── In-memory sessions ────────────────────────────────────────
sessions: dict[str, Session] = {}


# ── Request/Response models ───────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = ""
    image: bool = False  # True if user "sent a photo"
    language: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    state: str
    bot_messages: list[str]
    progress: float  # 0.0 - 1.0
    personal_info: dict | None = None
    document_type: str | None = None
    is_complete: bool = False
    reference_id: str | None = None


class DemoStats(BaseModel):
    active_sessions: int
    completed_sessions: int
    avg_completion_time: str
    languages_used: list[str]


# ── State progress mapping ───────────────────────────────────
STATE_PROGRESS = {
    KYCState.AWAITING_CONSENT: 0.0,
    KYCState.COLLECTING_NAME: 0.1,
    KYCState.COLLECTING_DOB: 0.2,
    KYCState.COLLECTING_NATIONALITY: 0.3,
    KYCState.COLLECTING_ADDRESS: 0.4,
    KYCState.SELECTING_DOCUMENT: 0.5,
    KYCState.UPLOADING_DOC_FRONT: 0.6,
    KYCState.UPLOADING_DOC_BACK: 0.7,
    KYCState.UPLOADING_SELFIE: 0.8,
    KYCState.REVIEWING: 0.9,
    KYCState.SUBMITTED: 0.95,
    KYCState.APPROVED: 1.0,
    KYCState.REJECTED: 1.0,
    KYCState.CANCELLED: 1.0,
}

DOC_LABELS = {
    "passport": {"en": "Passport", "zh": "护照"},
    "national_id": {"en": "National ID Card", "zh": "身份证"},
    "drivers_license": {"en": "Driver's License", "zh": "驾驶证"},
}


def _doc_label(doc_type: str | None, lang: str) -> str:
    if doc_type and doc_type in DOC_LABELS:
        return DOC_LABELS[doc_type].get(lang, DOC_LABELS[doc_type]["en"])
    return doc_type or ""


def _build_review(session: Session, lang: str) -> str:
    pi = session.personal_info
    doc_label = _doc_label(session.document.doc_type, lang)
    back_status = ""
    if session.needs_doc_back:
        ok = "✅" if session.document.back_image_path else "❌"
        back_label = "Back" if lang == "en" else "背面"
        back_status = f"\n   {back_label}: {ok}"

    header = get("review_header", lang=lang)
    body = get(
        "review_body",
        lang=lang,
        full_name=pi.full_name or "N/A",
        date_of_birth=pi.date_of_birth or "N/A",
        nationality=pi.nationality or "N/A",
        address=pi.address or "N/A",
        document_type=doc_label,
        back_status=back_status,
    )
    confirm = get("review_confirm", lang=lang)
    return f"{header}\n\n{body}{confirm}"


def _make_response(session: Session, bot_messages: list[str]) -> ChatResponse:
    return ChatResponse(
        session_id=session.session_id,
        state=session.state,
        bot_messages=bot_messages,
        progress=STATE_PROGRESS.get(session.state, 0.0),
        personal_info={
            "full_name": session.personal_info.full_name,
            "date_of_birth": session.personal_info.date_of_birth,
            "nationality": session.personal_info.nationality,
            "address": session.personal_info.address,
        },
        document_type=session.document.doc_type,
        is_complete=session.state in {KYCState.APPROVED, KYCState.SUBMITTED},
        reference_id=session.session_id if session.state in {KYCState.SUBMITTED, KYCState.APPROVED} else None,
    )


# ── API Endpoints ─────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Process a chat message through the KYC flow."""
    text = req.message.strip()
    lang = req.language or detect_language(text) or "en"

    # Create or load session
    if req.session_id and req.session_id in sessions:
        session = sessions[req.session_id]
    else:
        session = Session(user_id=f"demo_{uuid.uuid4().hex[:8]}")
        session.language = lang
        sessions[session.session_id] = session
        welcome = get("welcome", lang=lang)
        return _make_response(session, [welcome])

    session.language = lang
    state = session.state

    # Handle terminal states
    if session.is_terminal:
        if can_retry(session):
            return _make_response(session, ["Type /start_kyc to try again."])
        return _make_response(session, [get("already_approved", lang=lang)])

    # ── AWAITING_CONSENT ──
    if state == KYCState.AWAITING_CONSENT:
        positive = {"yes", "y", "agree", "ok", "sure", "是", "同意", "好", "好的", "start"}
        negative = {"no", "n", "cancel", "否", "不", "取消"}
        lower = text.lower()
        if lower in positive:
            advance(session)
            return _make_response(session, [get("collecting_name", lang=lang)])
        elif lower in negative:
            session.advance_to(KYCState.CANCELLED)
            return _make_response(session, [get("cancelled", lang=lang)])
        return _make_response(session, [get("welcome", lang=lang)])

    # ── COLLECTING_NAME ──
    if state == KYCState.COLLECTING_NAME:
        ok, val = validate_name(text)
        if not ok:
            return _make_response(session, [val])
        session.personal_info.full_name = val
        advance(session)
        return _make_response(session, [get("collecting_dob", lang=lang)])

    # ── COLLECTING_DOB ──
    if state == KYCState.COLLECTING_DOB:
        ok, val = validate_date_of_birth(text)
        if not ok:
            return _make_response(session, [val])
        session.personal_info.date_of_birth = val
        advance(session)
        return _make_response(session, [get("collecting_nationality", lang=lang)])

    # ── COLLECTING_NATIONALITY ──
    if state == KYCState.COLLECTING_NATIONALITY:
        ok, val = validate_nationality(text)
        if not ok:
            return _make_response(session, [val])
        session.personal_info.nationality = val
        advance(session)
        return _make_response(session, [get("collecting_address", lang=lang)])

    # ── COLLECTING_ADDRESS ──
    if state == KYCState.COLLECTING_ADDRESS:
        ok, val = validate_address(text)
        if not ok:
            return _make_response(session, [val])
        session.personal_info.address = val
        advance(session)
        return _make_response(session, [get("selecting_document", lang=lang)])

    # ── SELECTING_DOCUMENT ──
    if state == KYCState.SELECTING_DOCUMENT:
        ok, val = validate_document_type(text)
        if not ok:
            return _make_response(session, [val])
        session.document.doc_type = DocumentType(val)
        advance(session)
        doc_label = _doc_label(session.document.doc_type, lang)
        return _make_response(session, [get("uploading_doc_front", lang=lang, document_type=doc_label)])

    # ── UPLOADING_DOC_FRONT ──
    if state == KYCState.UPLOADING_DOC_FRONT:
        if not req.image:
            return _make_response(session, ["📷 Please send a photo of your document." if lang == "en" else "📷 请发送您证件的照片。"])
        session.document.front_image_path = "demo_front.jpg"
        advance(session)
        if session.state == KYCState.UPLOADING_DOC_BACK:
            return _make_response(session, [get("uploading_doc_back", lang=lang)])
        return _make_response(session, [get("uploading_selfie", lang=lang)])

    # ── UPLOADING_DOC_BACK ──
    if state == KYCState.UPLOADING_DOC_BACK:
        if not req.image:
            return _make_response(session, ["📷 Please send a photo of the back of your document." if lang == "en" else "📷 请发送您证件背面的照片。"])
        session.document.back_image_path = "demo_back.jpg"
        advance(session)
        return _make_response(session, [get("uploading_selfie", lang=lang)])

    # ── UPLOADING_SELFIE ──
    if state == KYCState.UPLOADING_SELFIE:
        if not req.image:
            return _make_response(session, ["📷 Please send a selfie." if lang == "en" else "📷 请发送一张自拍照。"])
        session.selfie.image_path = "demo_selfie.jpg"
        advance(session)
        return _make_response(session, [_build_review(session, lang)])

    # ── REVIEWING ──
    if state == KYCState.REVIEWING:
        confirm = {"confirm", "yes", "y", "ok", "确认", "是"}
        edit = {"edit", "modify", "change", "修改", "编辑", "重新"}
        lower = text.lower()
        if lower in confirm:
            session.verification.status = VerificationStatus.PROCESSING
            advance(session)
            msgs = [get("submitted", lang=lang, session_id=session.session_id)]
            # Auto-approve for demo
            await asyncio.sleep(0.5)
            session.verification.status = VerificationStatus.APPROVED
            session.advance_to(KYCState.APPROVED)
            msgs.append(get("approved", lang=lang))
            return _make_response(session, msgs)
        elif lower in edit:
            reset_for_retry(session)
            session.state = KYCState.AWAITING_CONSENT
            return _make_response(session, [get("welcome", lang=lang)])
        return _make_response(session, [_build_review(session, lang)])

    return _make_response(session, [get("error", lang=lang)])


@app.post("/api/start")
async def start_session(req: ChatRequest):
    """Create a new KYC session."""
    lang = req.language or "en"
    session = Session(user_id=f"demo_{uuid.uuid4().hex[:8]}")
    session.language = lang
    sessions[session.session_id] = session
    return _make_response(session, [get("welcome", lang=lang)])


@app.post("/api/reset")
async def reset_session(req: ChatRequest):
    """Reset a session."""
    if req.session_id and req.session_id in sessions:
        del sessions[req.session_id]
    return {"status": "reset"}


@app.get("/api/stats")
async def get_stats():
    """Get demo statistics."""
    completed = sum(1 for s in sessions.values() if s.state in {KYCState.APPROVED, KYCState.SUBMITTED})
    active = sum(1 for s in sessions.values() if not s.is_terminal)
    langs = list({s.language for s in sessions.values()})
    return DemoStats(
        active_sessions=active,
        completed_sessions=completed,
        avg_completion_time="3-5 min",
        languages_used=langs or ["en", "zh"],
    )


@app.get("/api/business/metrics")
async def business_metrics():
    """Return KYC market and business metrics."""
    return {
        "market": {
            "globalKycMarket2024": "$13.7B",
            "globalKycMarket2030": "$21.8B",
            "cagr": "8.1%",
            "digitalIdVerification": "$18.6B by 2028",
            "binanceUsers": "200M+",
            "binanceKycDaily": "~50,000 new verifications/day",
        },
        "traditionalKyc": {
            "avgCompletionTime": "8-15 minutes",
            "dropOffRate": "30-40%",
            "costPerVerification": "$2-5",
            "requiresWebview": True,
            "multiStepRedirects": True,
        },
        "chatKyc": {
            "avgCompletionTime": "3-5 minutes",
            "expectedDropOff": "10-15%",
            "costPerVerification": "$0.50-1",
            "zeroFrontend": True,
            "autoLanguageDetect": True,
        },
        "competitors": [
            {
                "name": "Jumio",
                "type": "SDK/WebView",
                "chatBased": False,
                "languages": 36,
                "avgTime": "8 min",
                "pricing": "$2-5/verification",
                "strength": "Market leader, 300M+ verifications",
                "weakness": "Heavy SDK, requires app integration",
            },
            {
                "name": "Onfido",
                "type": "SDK/API",
                "chatBased": False,
                "languages": 45,
                "avgTime": "6 min",
                "pricing": "$1-3/verification",
                "strength": "AI-first, good UX",
                "weakness": "No chat-native option",
            },
            {
                "name": "Sumsub",
                "type": "SDK/WebView/API",
                "chatBased": False,
                "languages": 30,
                "avgTime": "5 min",
                "pricing": "$0.5-2/verification",
                "strength": "Flexible, crypto-friendly",
                "weakness": "Still requires redirects",
            },
            {
                "name": "Binance Chat KYC",
                "type": "Telegram Bot (Chat-native)",
                "chatBased": True,
                "languages": "Auto-detect (7+)",
                "avgTime": "3-5 min",
                "pricing": "$0.50-1/verification",
                "strength": "Zero UI, zero redirects, 200M user base",
                "weakness": "New approach, needs validation",
            },
        ],
        "scenarios": [
            {
                "icon": "💬",
                "title": "Chat-Native KYC",
                "titleZh": "聊天式 KYC",
                "desc": "Users verify identity entirely within Telegram/WhatsApp — no app switches, no WebView, no SDK integration.",
                "descZh": "用户完全在 Telegram/WhatsApp 内完成身份验证 — 无需跳转 App、无需 WebView、无需 SDK 集成。",
                "revenue": "Save $1-4 per verification vs traditional providers",
                "revenueZh": "每次验证节省 $1-4（对比传统供应商）",
            },
            {
                "icon": "🌍",
                "title": "Global Reach",
                "titleZh": "全球覆盖",
                "desc": "Telegram has 900M+ users globally. Meet users where they already are — no download required.",
                "descZh": "Telegram 全球 9亿+ 用户。在用户已有的平台触达他们 — 无需下载任何东西。",
                "revenue": "15-25% increase in KYC completion rate",
                "revenueZh": "KYC 完成率提升 15-25%",
            },
            {
                "icon": "🤖",
                "title": "AI-Powered Validation",
                "titleZh": "AI 驱动验证",
                "desc": "Real-time document quality check, auto language detection, intelligent retry guidance.",
                "descZh": "实时证件质量检查、自动语言检测、智能重试引导。",
                "revenue": "Reduce manual review by 60%",
                "revenueZh": "减少 60% 人工审核",
            },
            {
                "icon": "🔗",
                "title": "Binance Ecosystem Integration",
                "titleZh": "币安生态集成",
                "desc": "Seamless KYC → Binance account activation. Verify once, trade immediately.",
                "descZh": "无缝衔接 KYC → 币安账户激活。一次验证，立即交易。",
                "revenue": "Reduce onboarding friction, increase new user conversion 20%+",
                "revenueZh": "降低注册摩擦，新用户转化率提升 20%+",
            },
            {
                "icon": "📊",
                "title": "Analytics & Compliance",
                "titleZh": "数据分析与合规",
                "desc": "Full audit trail in chat logs. Compliance-ready with GDPR/CCPA data handling.",
                "descZh": "聊天记录即完整审计追踪。内置 GDPR/CCPA 数据处理合规。",
                "revenue": "Reduce compliance costs 30%",
                "revenueZh": "合规成本降低 30%",
            },
            {
                "icon": "🔌",
                "title": "White-Label / BaaS",
                "titleZh": "白标 / KYC 即服务",
                "desc": "Offer chat-based KYC as a service to other exchanges, DeFi protocols, fintech apps.",
                "descZh": "将聊天式 KYC 作为服务提供给其他交易所、DeFi 协议、金融科技应用。",
                "revenue": "$5-20M annual revenue from licensing",
                "revenueZh": "许可收入年化 $5-20M",
            },
        ],
        "risks": [
            {"risk": "Regulatory", "riskZh": "监管风险", "probability": "Medium", "impact": "High", "mitigation": "Work with compliance team early, support all required document types per jurisdiction"},
            {"risk": "Photo Quality", "riskZh": "照片质量", "probability": "High", "impact": "Medium", "mitigation": "AI-powered quality check before submission, clear guidance prompts"},
            {"risk": "Fraud/Deepfake", "riskZh": "欺诈/深度伪造", "probability": "Medium", "impact": "High", "mitigation": "Liveness detection, cross-reference with existing databases"},
            {"risk": "User Adoption", "riskZh": "用户接受度", "probability": "Low", "impact": "Medium", "mitigation": "A/B test vs traditional flow, measure completion rates"},
            {"risk": "Platform Dependency", "riskZh": "平台依赖", "probability": "Low", "impact": "Medium", "mitigation": "Multi-platform support (Telegram, WhatsApp, in-app chat)"},
        ],
    }


@app.get("/api/business/calculate")
async def business_calculate(
    daily_verifications: int = 50000,
    traditional_cost: float = 3.0,
    chat_cost: float = 0.75,
    completion_rate_boost: float = 20.0,
):
    """Revenue/savings calculator."""
    daily_savings = daily_verifications * (traditional_cost - chat_cost)
    monthly_savings = daily_savings * 30
    yearly_savings = daily_savings * 365

    extra_daily = daily_verifications * (completion_rate_boost / 100)
    extra_monthly = extra_daily * 30
    extra_yearly = extra_daily * 365

    return {
        "input": {
            "dailyVerifications": f"{daily_verifications:,}",
            "traditionalCost": f"${traditional_cost:.2f}",
            "chatCost": f"${chat_cost:.2f}",
            "completionRateBoost": f"{completion_rate_boost}%",
        },
        "costSavings": {
            "daily": f"${daily_savings:,.0f}",
            "monthly": f"${monthly_savings:,.0f}",
            "yearly": f"${yearly_savings:,.0f}",
        },
        "additionalUsers": {
            "daily": f"{extra_daily:,.0f}",
            "monthly": f"{extra_monthly:,.0f}",
            "yearly": f"{extra_yearly:,.0f}",
        },
        "roi": f"{((traditional_cost - chat_cost) / traditional_cost * 100):.0f}% cost reduction",
    }


# ── Static files ──────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent.parent / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static_assets")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/user-demo")
@app.get("/user-demo.html")
async def user_demo():
    return FileResponse(str(STATIC_DIR / "user-demo.html"))


@app.get("/business")
@app.get("/business.html")
async def business():
    return FileResponse(str(STATIC_DIR / "business.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8099)
