"""Persistent session storage backed by JSON files."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from binance_kyc.models.session import Session

logger = structlog.get_logger()


class SessionStore:
    """Read/write KYC sessions as individual JSON files.

    Each user gets ``<sessions_dir>/<user_id>.json``.
    """

    def __init__(self, sessions_dir: Path) -> None:
        self._dir = sessions_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, user_id: str) -> Path:
        # Sanitise user_id to prevent path traversal
        safe_id = "".join(c for c in user_id if c.isalnum() or c in ("_", "-", "+"))
        return self._dir / f"{safe_id}.json"

    def load(self, user_id: str) -> Session | None:
        """Load a session from disk, or return ``None``."""
        path = self._path_for(user_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Session.model_validate(data)
        except Exception:
            logger.warning("corrupt_session_file", path=str(path))
            return None

    def save(self, session: Session) -> None:
        """Persist a session to disk."""
        session.touch()
        path = self._path_for(session.user_id)
        path.write_text(
            session.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.debug("session_saved", user_id=session.user_id, state=session.state)

    def delete(self, user_id: str) -> None:
        """Remove a user's session and uploads."""
        path = self._path_for(user_id)
        if path.exists():
            path.unlink()
            logger.info("session_deleted", user_id=user_id)

    def exists(self, user_id: str) -> bool:
        """Check whether a session file exists."""
        return self._path_for(user_id).exists()
