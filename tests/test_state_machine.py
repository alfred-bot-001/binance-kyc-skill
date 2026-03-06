"""Tests for the KYC state machine."""

from __future__ import annotations

import pytest

from binance_kyc.models.enums import DocumentType, KYCState, VerificationStatus
from binance_kyc.models.session import Session
from binance_kyc.services.state_machine import advance, can_retry, next_state, reset_for_retry


class TestNextState:
    def test_consent_to_name(self):
        s = Session(user_id="u1")
        assert next_state(s) == KYCState.COLLECTING_NAME

    def test_name_to_dob(self):
        s = Session(user_id="u1", state=KYCState.COLLECTING_NAME)
        assert next_state(s) == KYCState.COLLECTING_DOB

    def test_full_linear_flow(self):
        """Walk through the entire flow for a national ID (double-sided)."""
        s = Session(user_id="u1")
        s.document.doc_type = DocumentType.NATIONAL_ID

        expected = [
            KYCState.COLLECTING_NAME,
            KYCState.COLLECTING_DOB,
            KYCState.COLLECTING_NATIONALITY,
            KYCState.COLLECTING_ADDRESS,
            KYCState.SELECTING_DOCUMENT,
            KYCState.UPLOADING_DOC_FRONT,
            KYCState.UPLOADING_DOC_BACK,
            KYCState.UPLOADING_SELFIE,
            KYCState.REVIEWING,
            KYCState.SUBMITTED,
        ]

        for exp in expected:
            nxt = next_state(s)
            assert nxt == exp, f"Expected {exp}, got {nxt} from {s.state}"
            s.state = nxt

    def test_passport_skips_back(self):
        """Passport should skip the doc-back state."""
        s = Session(user_id="u1", state=KYCState.UPLOADING_DOC_FRONT)
        s.document.doc_type = DocumentType.PASSPORT
        assert next_state(s) == KYCState.UPLOADING_SELFIE

    def test_national_id_needs_back(self):
        s = Session(user_id="u1", state=KYCState.UPLOADING_DOC_FRONT)
        s.document.doc_type = DocumentType.NATIONAL_ID
        assert next_state(s) == KYCState.UPLOADING_DOC_BACK

    def test_terminal_returns_none(self):
        s = Session(user_id="u1", state=KYCState.APPROVED)
        assert next_state(s) is None


class TestAdvance:
    def test_advances_state(self):
        s = Session(user_id="u1")
        old_state = s.state
        result = advance(s)
        assert result == KYCState.COLLECTING_NAME
        assert s.state == KYCState.COLLECTING_NAME
        assert s.state != old_state

    def test_raises_on_terminal(self):
        s = Session(user_id="u1", state=KYCState.APPROVED)
        with pytest.raises(ValueError, match="terminal"):
            advance(s)

    def test_updates_timestamp(self):
        s = Session(user_id="u1")
        old_ts = s.updated_at
        advance(s)
        assert s.updated_at >= old_ts


class TestRetry:
    def test_can_retry_rejected(self):
        s = Session(user_id="u1", state=KYCState.REJECTED)
        assert can_retry(s) is True

    def test_can_retry_cancelled(self):
        s = Session(user_id="u1", state=KYCState.CANCELLED)
        assert can_retry(s) is True

    def test_cannot_retry_approved(self):
        s = Session(user_id="u1", state=KYCState.APPROVED)
        assert can_retry(s) is False

    def test_cannot_retry_in_progress(self):
        s = Session(user_id="u1", state=KYCState.COLLECTING_NAME)
        assert can_retry(s) is False

    def test_reset_clears_data(self):
        s = Session(user_id="u1", state=KYCState.REJECTED)
        s.personal_info.full_name = "Test"
        s.document.doc_type = DocumentType.PASSPORT
        reset_for_retry(s)
        assert s.state == KYCState.AWAITING_CONSENT
        assert s.personal_info.full_name is None
        assert s.document.doc_type is None

    def test_reset_raises_if_not_retryable(self):
        s = Session(user_id="u1", state=KYCState.COLLECTING_NAME)
        with pytest.raises(ValueError):
            reset_for_retry(s)
