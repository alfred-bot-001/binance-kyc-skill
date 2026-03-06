"""Tests for message templates."""

from __future__ import annotations

from binance_kyc.messages import detect_language, get


class TestDetectLanguage:
    def test_english(self):
        assert detect_language("Hello world") == "en"

    def test_chinese(self):
        assert detect_language("你好世界") == "zh"

    def test_japanese(self):
        assert detect_language("こんにちは") == "ja"

    def test_korean(self):
        assert detect_language("안녕하세요") == "ko"

    def test_russian(self):
        assert detect_language("Привет мир") == "ru"

    def test_mixed_defaults_to_detected(self):
        assert detect_language("Hello 你好") == "zh"


class TestGetMessage:
    def test_english_welcome(self):
        msg = get("welcome", lang="en")
        assert "Welcome" in msg
        assert "Binance" in msg

    def test_chinese_welcome(self):
        msg = get("welcome", lang="zh")
        assert "欢迎" in msg

    def test_placeholder_substitution(self):
        msg = get("submitted", lang="en", session_id="KYC-TEST-123")
        assert "KYC-TEST-123" in msg

    def test_missing_key_returns_fallback(self):
        msg = get("nonexistent_key_xyz", lang="en")
        assert "missing" in msg.lower()

    def test_fallback_to_english(self):
        # Japanese file doesn't exist, should fall back to English
        msg = get("welcome", lang="ja")
        assert "Welcome" in msg
