"""Tests for the liveness check service."""

from __future__ import annotations

from binance_kyc.models.enums import KYCState, LivenessStatus
from binance_kyc.models.session import Session
from binance_kyc.services.liveness import (
    can_retry_liveness,
    generate_liveness_url,
    is_liveness_expired,
    process_liveness_callback,
)


class TestGenerateLivenessUrl:
    def test_generates_url(self):
        s = Session(user_id="u1", state=KYCState.AWAITING_LIVENESS)
        url = generate_liveness_url(s, demo_mode=True)
        assert "kyc-demo.binance.com" in url
        assert s.session_id in url
        assert s.liveness.attempts == 1
        assert s.liveness.url == url

    def test_increments_attempts(self):
        s = Session(user_id="u1", state=KYCState.AWAITING_LIVENESS)
        generate_liveness_url(s, demo_mode=True)
        assert s.liveness.attempts == 1
        generate_liveness_url(s, demo_mode=True)
        assert s.liveness.attempts == 2

    def test_production_url(self):
        s = Session(user_id="u1", state=KYCState.AWAITING_LIVENESS)
        url = generate_liveness_url(s, demo_mode=False)
        assert "kyc.binance.com" in url
        assert "kyc-demo" not in url

    def test_includes_language(self):
        s = Session(user_id="u1", state=KYCState.AWAITING_LIVENESS, language="zh")
        url = generate_liveness_url(s, demo_mode=True)
        assert "lang=zh" in url

    def test_sets_expiry(self):
        s = Session(user_id="u1", state=KYCState.AWAITING_LIVENESS)
        generate_liveness_url(s, demo_mode=True)
        assert s.liveness.expires_at is not None


class TestProcessLivenessCallback:
    def test_passed(self):
        s = Session(user_id="u1", state=KYCState.AWAITING_LIVENESS)
        process_liveness_callback(s, passed=True, confidence=0.95)
        assert s.liveness.status == LivenessStatus.PASSED

    def test_failed(self):
        s = Session(user_id="u1", state=KYCState.AWAITING_LIVENESS)
        process_liveness_callback(s, passed=False, error_code="FACE_NOT_DETECTED")
        assert s.liveness.status == LivenessStatus.FAILED


class TestCanRetryLiveness:
    def test_can_retry_initially(self):
        s = Session(user_id="u1")
        assert can_retry_liveness(s) is True

    def test_cannot_retry_after_max(self):
        s = Session(user_id="u1")
        s.liveness.attempts = 3
        assert can_retry_liveness(s) is False

    def test_can_retry_after_one(self):
        s = Session(user_id="u1")
        s.liveness.attempts = 1
        assert can_retry_liveness(s) is True


class TestIsLivenessExpired:
    def test_not_expired_initially(self):
        s = Session(user_id="u1")
        assert is_liveness_expired(s) is False

    def test_not_expired_after_generate(self):
        s = Session(user_id="u1")
        generate_liveness_url(s, demo_mode=True)
        assert is_liveness_expired(s) is False
