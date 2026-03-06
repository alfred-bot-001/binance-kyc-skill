"""Telegram bot command and message handlers.

This module registers all handlers with ``python-telegram-bot`` and
delegates business logic to the service layer.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import structlog
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from binance_kyc.config import Settings
from binance_kyc.messages import detect_language, get
from binance_kyc.models.enums import (
    DOUBLE_SIDE_DOCUMENTS,
    DocumentType,
    KYCState,
    VerificationStatus,
)
from binance_kyc.models.session import Session
from binance_kyc.services.session_store import SessionStore
from binance_kyc.services.state_machine import advance, can_retry, reset_for_retry
from binance_kyc.services.validators import (
    validate_address,
    validate_date_of_birth,
    validate_document_type,
    validate_name,
    validate_nationality,
)

logger = structlog.get_logger()

# ── Helpers ──────────────────────────────────────────────────


def _user_id(update: Update) -> str:
    """Extract a stable user identifier from the Telegram update."""
    assert update.effective_user is not None  # noqa: S101
    return str(update.effective_user.id)


def _lang(session: Session | None, text: str = "") -> str:
    """Return the session language, or detect from *text*."""
    if session and session.language:
        return session.language
    return detect_language(text)


def _doc_label(doc_type: DocumentType | None, lang: str) -> str:
    """Human-readable document-type label."""
    types = get("doc_types", lang=lang)
    if isinstance(types, dict) and doc_type:
        return types.get(doc_type.value, str(doc_type))
    return str(doc_type or "")


async def _reply(update: Update, text: str) -> None:
    """Send a reply message."""
    assert update.message is not None  # noqa: S101
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Command Handlers ─────────────────────────────────────────


async def cmd_start_kyc(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/start_kyc`` — begin a new KYC session."""
    store: SessionStore = ctx.bot_data["store"]
    settings: Settings = ctx.bot_data["settings"]
    uid = _user_id(update)

    existing = store.load(uid)
    if existing and existing.state == KYCState.APPROVED:
        lang = _lang(existing)
        await _reply(update, get("already_approved", lang=lang))
        return

    # Create fresh session
    session = Session(user_id=uid)
    text = update.message.text or ""
    session.language = detect_language(text)
    store.save(session)

    lang = session.language
    await _reply(update, get("welcome", lang=lang))
    logger.info("kyc_started", user_id=uid, session_id=session.session_id)


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/status`` — show current verification status."""
    store: SessionStore = ctx.bot_data["store"]
    uid = _user_id(update)
    session = store.load(uid)

    if not session:
        await _reply(update, "No verification found. Type /start_kyc to begin.")
        return

    lang = _lang(session)
    status_map = {
        KYCState.APPROVED: get("approved", lang=lang),
        KYCState.REJECTED: get("rejected", lang=lang, reason=session.verification.rejection_reason or "N/A"),
        KYCState.SUBMITTED: get("submitted", lang=lang, session_id=session.session_id),
        KYCState.CANCELLED: get("cancelled", lang=lang),
    }
    msg = status_map.get(session.state, f"📋 Current step: `{session.state}`\nReference: `{session.session_id}`")
    await _reply(update, msg)


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/cancel`` — cancel the current KYC session."""
    store: SessionStore = ctx.bot_data["store"]
    uid = _user_id(update)
    session = store.load(uid)

    if not session or session.is_terminal:
        await _reply(update, "No active verification to cancel.")
        return

    lang = _lang(session)
    session.advance_to(KYCState.CANCELLED)
    store.save(session)
    store.delete(uid)
    await _reply(update, get("cancelled", lang=lang))
    logger.info("kyc_cancelled", user_id=uid)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/help``."""
    store: SessionStore = ctx.bot_data["store"]
    uid = _user_id(update)
    session = store.load(uid)
    lang = _lang(session, update.message.text or "")
    await _reply(update, get("help", lang=lang))


# ── Message Handler (main flow) ──────────────────────────────


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: C901
    """Process free-text and photo messages through the KYC state machine."""
    store: SessionStore = ctx.bot_data["store"]
    settings: Settings = ctx.bot_data["settings"]
    uid = _user_id(update)
    session = store.load(uid)

    if not session:
        await _reply(update, "Type /start_kyc to begin identity verification.")
        return

    if session.is_terminal:
        if can_retry(session):
            await _reply(update, "Type /start_kyc to try again.")
        return

    lang = _lang(session)
    text = (update.message.text or "").strip()
    state = session.state

    # ── AWAITING_CONSENT ──────────────────────────────────────
    if state == KYCState.AWAITING_CONSENT:
        positive = {"yes", "y", "agree", "ok", "sure", "是", "同意", "好", "好的"}
        negative = {"no", "n", "cancel", "否", "不", "取消"}
        lower = text.lower()
        if lower in positive:
            advance(session)
            store.save(session)
            await _reply(update, get("collecting_name", lang=lang))
        elif lower in negative:
            session.advance_to(KYCState.CANCELLED)
            store.save(session)
            await _reply(update, get("cancelled", lang=lang))
        else:
            await _reply(update, get("welcome", lang=lang))
        return

    # ── COLLECTING_NAME ───────────────────────────────────────
    if state == KYCState.COLLECTING_NAME:
        ok, val = validate_name(text)
        if not ok:
            await _reply(update, val)
            return
        session.personal_info.full_name = val
        advance(session)
        store.save(session)
        await _reply(update, get("collecting_dob", lang=lang))
        return

    # ── COLLECTING_DOB ────────────────────────────────────────
    if state == KYCState.COLLECTING_DOB:
        ok, val = validate_date_of_birth(text)
        if not ok:
            await _reply(update, val)
            return
        session.personal_info.date_of_birth = val
        advance(session)
        store.save(session)
        await _reply(update, get("collecting_nationality", lang=lang))
        return

    # ── COLLECTING_NATIONALITY ────────────────────────────────
    if state == KYCState.COLLECTING_NATIONALITY:
        ok, val = validate_nationality(text)
        if not ok:
            await _reply(update, val)
            return
        session.personal_info.nationality = val
        advance(session)
        store.save(session)
        await _reply(update, get("collecting_address", lang=lang))
        return

    # ── COLLECTING_ADDRESS ────────────────────────────────────
    if state == KYCState.COLLECTING_ADDRESS:
        ok, val = validate_address(text)
        if not ok:
            await _reply(update, val)
            return
        session.personal_info.address = val
        advance(session)
        store.save(session)
        await _reply(update, get("selecting_document", lang=lang))
        return

    # ── SELECTING_DOCUMENT ────────────────────────────────────
    if state == KYCState.SELECTING_DOCUMENT:
        ok, val = validate_document_type(text)
        if not ok:
            await _reply(update, val)
            return
        session.document.doc_type = DocumentType(val)
        advance(session)
        store.save(session)
        doc_label = _doc_label(session.document.doc_type, lang)
        await _reply(update, get("uploading_doc_front", lang=lang, document_type=doc_label))
        return

    # ── UPLOADING_DOC_FRONT ───────────────────────────────────
    if state == KYCState.UPLOADING_DOC_FRONT:
        photo = _extract_photo(update)
        if not photo:
            await _reply(update, "Please send a photo of your document.")
            return
        path = await _save_photo(photo, uid, "doc_front", settings, ctx)
        session.document.front_image_path = str(path)
        advance(session)
        store.save(session)
        if session.state == KYCState.UPLOADING_DOC_BACK:
            await _reply(update, get("uploading_doc_back", lang=lang))
        else:
            await _reply(update, get("uploading_selfie", lang=lang))
        return

    # ── UPLOADING_DOC_BACK ────────────────────────────────────
    if state == KYCState.UPLOADING_DOC_BACK:
        photo = _extract_photo(update)
        if not photo:
            await _reply(update, "Please send a photo of the back of your document.")
            return
        path = await _save_photo(photo, uid, "doc_back", settings, ctx)
        session.document.back_image_path = str(path)
        advance(session)
        store.save(session)
        await _reply(update, get("uploading_selfie", lang=lang))
        return

    # ── UPLOADING_SELFIE ──────────────────────────────────────
    if state == KYCState.UPLOADING_SELFIE:
        photo = _extract_photo(update)
        if not photo:
            await _reply(update, "Please send a selfie photo.")
            return
        path = await _save_photo(photo, uid, "selfie", settings, ctx)
        session.selfie.image_path = str(path)
        advance(session)
        store.save(session)
        await _reply(update, _build_review(session, lang))
        return

    # ── REVIEWING ─────────────────────────────────────────────
    if state == KYCState.REVIEWING:
        confirm = {"confirm", "yes", "y", "ok", "确认", "是"}
        edit = {"edit", "modify", "change", "修改", "编辑", "重新"}
        lower = text.lower()
        if lower in confirm:
            session.verification.status = VerificationStatus.PROCESSING
            session.verification.submitted_at = datetime.now(UTC)
            advance(session)
            store.save(session)
            await _reply(update, get("submitted", lang=lang, session_id=session.session_id))
            # In demo mode, auto-approve after delay
            if settings.mode.value == "demo":
                asyncio.create_task(_demo_approve(store, session, update, ctx))
        elif lower in edit:
            reset_for_retry(session)
            session.state = KYCState.AWAITING_CONSENT
            store.save(session)
            await _reply(update, get("welcome", lang=lang))
        else:
            await _reply(update, _build_review(session, lang))
        return


# ── Photo helpers ────────────────────────────────────────────


def _extract_photo(update: Update):
    """Get the best-resolution photo from the update, or None."""
    if update.message and update.message.photo:
        return update.message.photo[-1]  # highest resolution
    if update.message and update.message.document:
        mime = update.message.document.mime_type or ""
        if mime.startswith("image/"):
            return update.message.document
    return None


async def _save_photo(photo, user_id: str, label: str, settings: Settings, ctx) -> Path:
    """Download and save a photo to the uploads directory."""
    uploads = settings.uploads_dir / user_id
    uploads.mkdir(parents=True, exist_ok=True)
    file = await ctx.bot.get_file(photo.file_id)
    ext = "jpg"
    dest = uploads / f"{label}.{ext}"
    await file.download_to_drive(str(dest))
    logger.info("photo_saved", user_id=user_id, label=label, path=str(dest))
    return dest


# ── Review builder ───────────────────────────────────────────


def _build_review(session: Session, lang: str) -> str:
    """Build the review summary message from session data."""
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


# ── Demo auto-approve ────────────────────────────────────────


async def _demo_approve(store: SessionStore, session: Session, update: Update, ctx) -> None:
    """Simulate verification approval after a short delay (demo mode only)."""
    await asyncio.sleep(10)
    session = store.load(session.user_id)
    if session and session.state == KYCState.SUBMITTED:
        session.verification.status = VerificationStatus.APPROVED
        session.verification.completed_at = datetime.now(UTC)
        session.verification.result = "approved"
        session.advance_to(KYCState.APPROVED)
        store.save(session)
        lang = _lang(session)
        await _reply(update, get("approved", lang=lang))
        logger.info("demo_auto_approved", user_id=session.user_id)


# ── Application builder ─────────────────────────────────────


def build_app(settings: Settings) -> Application:
    """Create and configure the Telegram bot application."""
    settings.ensure_dirs()
    store = SessionStore(settings.sessions_dir)

    app = Application.builder().token(settings.telegram_token).build()
    app.bot_data["store"] = store
    app.bot_data["settings"] = settings

    # Register handlers (order matters)
    app.add_handler(CommandHandler("start_kyc", cmd_start_kyc))
    app.add_handler(CommandHandler("start", cmd_start_kyc))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
