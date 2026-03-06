"""Multi-language message templates for the KYC flow."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_MESSAGES_DIR = Path(__file__).parent
_CACHE: dict[str, dict[str, Any]] = {}


def _load(lang: str) -> dict[str, Any]:
    """Load and cache a language file."""
    if lang not in _CACHE:
        path = _MESSAGES_DIR / f"{lang}.json"
        if not path.exists():
            path = _MESSAGES_DIR / "en.json"
        _CACHE[lang] = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE[lang]


def get(key: str, lang: str = "en", **kwargs: str) -> str:
    """Retrieve a message template, with optional placeholder substitution.

    Example::

        get("submitted", lang="zh", session_id="KYC-20260306-AB12CD")
    """
    msgs = _load(lang)
    text = msgs.get(key, msgs.get(key, f"[missing:{key}]"))
    if kwargs:
        text = text.format(**kwargs)
    return text


def detect_language(text: str) -> str:
    """Detect language from Unicode character ranges.

    This is a lightweight heuristic — production systems should use a
    proper language-detection library.
    """
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    if re.search(r"[\u0400-\u04ff]", text):
        return "ru"
    if re.search(r"[\u0600-\u06ff]", text):
        return "ar"
    return "en"
