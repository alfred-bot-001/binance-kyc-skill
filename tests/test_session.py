"""Tests for session model."""

from __future__ import annotations

from binance_kyc.models.enums import DocumentType, KYCState
from binance_kyc.models.session import Session


class TestSession:
    def test_defaults(self):
        s = Session(user_id="u1")
        assert s.state == KYCState.AWAITING_CONSENT
        assert s.language == "en"
        assert s.session_id.startswith("KYC-")
        assert s.personal_info.full_name is None

    def test_is_terminal(self):
        assert Session(user_id="u1", state=KYCState.APPROVED).is_terminal
        assert Session(user_id="u1", state=KYCState.REJECTED).is_terminal
        assert Session(user_id="u1", state=KYCState.CANCELLED).is_terminal
        assert not Session(user_id="u1", state=KYCState.COLLECTING_NAME).is_terminal

    def test_needs_doc_back(self):
        s = Session(user_id="u1")
        s.document.doc_type = DocumentType.NATIONAL_ID
        assert s.needs_doc_back is True
        s.document.doc_type = DocumentType.PASSPORT
        assert s.needs_doc_back is False

    def test_liveness_defaults(self):
        s = Session(user_id="u1")
        assert s.liveness.status == "pending"
        assert s.liveness.attempts == 0
        assert s.liveness.can_retry is True

    def test_advance_to(self):
        s = Session(user_id="u1")
        old = s.updated_at
        s.advance_to(KYCState.COLLECTING_NAME)
        assert s.state == KYCState.COLLECTING_NAME
        assert s.updated_at >= old

    def test_json_round_trip(self):
        s = Session(user_id="u1")
        s.personal_info.full_name = "张三"
        s.document.doc_type = DocumentType.PASSPORT
        json_str = s.model_dump_json()
        s2 = Session.model_validate_json(json_str)
        assert s2.personal_info.full_name == "张三"
        assert s2.document.doc_type == DocumentType.PASSPORT
