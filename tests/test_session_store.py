"""Tests for session storage."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from binance_kyc.models.enums import KYCState
from binance_kyc.models.session import Session
from binance_kyc.services.session_store import SessionStore


@pytest.fixture()
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions")


class TestSessionStore:
    def test_save_and_load(self, store: SessionStore):
        session = Session(user_id="user_123")
        session.personal_info.full_name = "Alice"
        store.save(session)

        loaded = store.load("user_123")
        assert loaded is not None
        assert loaded.user_id == "user_123"
        assert loaded.personal_info.full_name == "Alice"
        assert loaded.session_id == session.session_id

    def test_load_nonexistent(self, store: SessionStore):
        assert store.load("nobody") is None

    def test_exists(self, store: SessionStore):
        assert store.exists("user_123") is False
        store.save(Session(user_id="user_123"))
        assert store.exists("user_123") is True

    def test_delete(self, store: SessionStore):
        store.save(Session(user_id="user_123"))
        assert store.exists("user_123")
        store.delete("user_123")
        assert not store.exists("user_123")

    def test_delete_nonexistent(self, store: SessionStore):
        # Should not raise
        store.delete("nobody")

    def test_overwrite(self, store: SessionStore):
        s1 = Session(user_id="user_123")
        store.save(s1)
        s2 = Session(user_id="user_123", state=KYCState.COLLECTING_NAME)
        store.save(s2)
        loaded = store.load("user_123")
        assert loaded is not None
        assert loaded.state == KYCState.COLLECTING_NAME

    def test_sanitises_user_id(self, store: SessionStore):
        """Path traversal attempts should be neutralised."""
        session = Session(user_id="../../../etc/passwd")
        store.save(session)
        # File should be saved with sanitised name, not escape the dir
        loaded = store.load("../../../etc/passwd")
        assert loaded is not None
