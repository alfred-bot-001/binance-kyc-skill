"""Liveness check service — generates verification URLs and processes callbacks.

In production, this calls Binance's liveness API to generate a secure
video-verification page URL. The user opens this URL in their browser,
completes the face scan, and we receive a webhook callback.

In demo mode, it generates a fake URL and auto-passes after a delay.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog

from binance_kyc.models.enums import LivenessStatus
from binance_kyc.models.session import Session

logger = structlog.get_logger()

# Liveness URL expiry time
LIVENESS_EXPIRY_MINUTES = 10

# Demo mode base URL
DEMO_LIVENESS_BASE = "https://kyc-demo.binance.com/liveness"

# Production base URL
PROD_LIVENESS_BASE = "https://kyc.binance.com/liveness"


def generate_liveness_url(
    session: Session,
    *,
    demo_mode: bool = True,
    api_base: str | None = None,
) -> str:
    """Generate a liveness check URL for the user.

    The user opens this URL in their browser to complete face verification.
    The URL contains a one-time session token and expires after 10 minutes.

    Args:
        session: The KYC session.
        demo_mode: If True, use demo URL.
        api_base: Override the API base URL.

    Returns:
        The liveness check URL to send to the user.
    """
    token = uuid.uuid4().hex
    expires = datetime.now(UTC) + timedelta(minutes=LIVENESS_EXPIRY_MINUTES)

    base = api_base or (DEMO_LIVENESS_BASE if demo_mode else PROD_LIVENESS_BASE)
    url = f"{base}?session={session.session_id}&token={token}&lang={session.language}"

    # Update session
    session.liveness.url = url
    session.liveness.status = LivenessStatus.PENDING
    session.liveness.attempts += 1
    session.liveness.expires_at = expires
    session.touch()

    logger.info(
        "liveness_url_generated",
        user_id=session.user_id,
        session_id=session.session_id,
        attempt=session.liveness.attempts,
        expires_at=expires.isoformat(),
    )

    return url


def process_liveness_callback(
    session: Session,
    *,
    passed: bool,
    confidence: float = 0.0,
    error_code: str | None = None,
) -> None:
    """Process a liveness check webhook callback.

    Called when Binance's liveness service sends back the result.

    Args:
        session: The KYC session.
        passed: Whether the liveness check passed.
        confidence: Face match confidence score (0-1).
        error_code: Error code if failed.
    """
    if passed:
        session.liveness.status = LivenessStatus.PASSED
        logger.info(
            "liveness_passed",
            user_id=session.user_id,
            confidence=confidence,
        )
    else:
        session.liveness.status = LivenessStatus.FAILED
        logger.warning(
            "liveness_failed",
            user_id=session.user_id,
            error_code=error_code,
            attempt=session.liveness.attempts,
        )
    session.touch()


def can_retry_liveness(session: Session) -> bool:
    """Whether the user can attempt liveness again."""
    return session.liveness.can_retry


def is_liveness_expired(session: Session) -> bool:
    """Whether the current liveness URL has expired."""
    return session.liveness.is_expired
