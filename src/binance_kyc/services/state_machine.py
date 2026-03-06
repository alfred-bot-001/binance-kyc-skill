"""KYC state-machine transitions and orchestration."""

from __future__ import annotations

import structlog

from binance_kyc.models.enums import (
    SINGLE_SIDE_DOCUMENTS,
    DocumentType,
    KYCState,
    VerificationStatus,
)
from binance_kyc.models.session import Session

logger = structlog.get_logger()

# Ordered linear flow (doc-back is conditionally skipped)
_TRANSITIONS: dict[KYCState, KYCState] = {
    KYCState.AWAITING_CONSENT: KYCState.COLLECTING_NAME,
    KYCState.COLLECTING_NAME: KYCState.COLLECTING_DOB,
    KYCState.COLLECTING_DOB: KYCState.COLLECTING_NATIONALITY,
    KYCState.COLLECTING_NATIONALITY: KYCState.COLLECTING_ADDRESS,
    KYCState.COLLECTING_ADDRESS: KYCState.SELECTING_DOCUMENT,
    KYCState.SELECTING_DOCUMENT: KYCState.UPLOADING_DOC_FRONT,
    # UPLOADING_DOC_FRONT → handled dynamically (skip back for passport)
    KYCState.UPLOADING_DOC_BACK: KYCState.UPLOADING_SELFIE,
    KYCState.UPLOADING_SELFIE: KYCState.REVIEWING,
    KYCState.REVIEWING: KYCState.SUBMITTED,
}


def next_state(session: Session) -> KYCState | None:
    """Determine the next state based on the current session.

    Returns ``None`` if no transition is defined (terminal state).
    """
    current = session.state

    # Special case: after front upload, skip back for single-side docs
    if current == KYCState.UPLOADING_DOC_FRONT:
        if session.document.doc_type in SINGLE_SIDE_DOCUMENTS:
            return KYCState.UPLOADING_SELFIE
        return KYCState.UPLOADING_DOC_BACK

    return _TRANSITIONS.get(current)


def advance(session: Session) -> KYCState:
    """Advance the session to its next state.

    Raises:
        ValueError: If the session is in a terminal state.
    """
    nxt = next_state(session)
    if nxt is None:
        msg = f"Cannot advance from terminal state: {session.state}"
        raise ValueError(msg)

    logger.info(
        "state_transition",
        user_id=session.user_id,
        from_state=session.state,
        to_state=nxt,
    )
    session.advance_to(nxt)
    return nxt


def can_retry(session: Session) -> bool:
    """Whether the user can restart their KYC attempt."""
    return session.state in {KYCState.REJECTED, KYCState.CANCELLED}


def reset_for_retry(session: Session) -> None:
    """Reset a rejected/cancelled session back to the beginning."""
    if not can_retry(session):
        msg = f"Cannot retry from state: {session.state}"
        raise ValueError(msg)

    session.state = KYCState.AWAITING_CONSENT
    session.personal_info.full_name = None
    session.personal_info.date_of_birth = None
    session.personal_info.nationality = None
    session.personal_info.address = None
    session.document.doc_type = None
    session.document.front_image_path = None
    session.document.back_image_path = None
    session.selfie.image_path = None
    session.verification.status = VerificationStatus.PENDING
    session.verification.submitted_at = None
    session.verification.result = None
    session.verification.rejection_reason = None
    session.touch()
