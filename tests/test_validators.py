"""Tests for input validators."""

from __future__ import annotations

import pytest

from binance_kyc.services.validators import (
    validate_address,
    validate_date_of_birth,
    validate_document_type,
    validate_image_meta,
    validate_name,
    validate_nationality,
)


# ── validate_name ────────────────────────────────────────────


class TestValidateName:
    def test_valid_name(self):
        ok, val = validate_name("John Doe")
        assert ok is True
        assert val == "John Doe"

    def test_valid_unicode_name(self):
        ok, val = validate_name("张三")
        assert ok is True
        assert val == "张三"

    def test_strips_whitespace(self):
        ok, val = validate_name("  Alice Smith  ")
        assert ok is True
        assert val == "Alice Smith"

    def test_too_short(self):
        ok, val = validate_name("A")
        assert ok is False
        assert "too short" in val.lower()

    def test_too_long(self):
        ok, val = validate_name("A" * 101)
        assert ok is False
        assert "too long" in val.lower()

    def test_all_symbols_rejected(self):
        ok, val = validate_name("!!@@##")
        assert ok is False

    def test_empty_string(self):
        ok, val = validate_name("")
        assert ok is False


# ── validate_date_of_birth ───────────────────────────────────


class TestValidateDateOfBirth:
    def test_valid_iso(self):
        ok, val = validate_date_of_birth("1990-01-15")
        assert ok is True
        assert val == "1990-01-15"

    def test_valid_slash_format(self):
        ok, val = validate_date_of_birth("15/01/1990")
        assert ok is True
        assert val == "1990-01-15"

    def test_valid_dot_format(self):
        ok, val = validate_date_of_birth("1990.01.15")
        assert ok is True
        assert val == "1990-01-15"

    def test_under_18(self):
        ok, val = validate_date_of_birth("2020-01-01")
        assert ok is False
        assert "18" in val

    def test_future_date(self):
        ok, val = validate_date_of_birth("2099-01-01")
        assert ok is False

    def test_invalid_format(self):
        ok, val = validate_date_of_birth("not-a-date")
        assert ok is False
        assert "YYYY-MM-DD" in val

    def test_very_old(self):
        ok, val = validate_date_of_birth("1800-01-01")
        assert ok is False
        assert "valid" in val.lower()


# ── validate_nationality ─────────────────────────────────────


class TestValidateNationality:
    def test_exact_country(self):
        ok, val = validate_nationality("United States")
        assert ok is True
        assert val == "United States"

    def test_alias(self):
        ok, val = validate_nationality("american")
        assert ok is True
        assert val == "United States"

    def test_chinese_alias(self):
        ok, val = validate_nationality("中国")
        assert ok is True
        assert val == "China"

    def test_case_insensitive(self):
        ok, val = validate_nationality("JAPAN")
        assert ok is True
        assert val == "Japan"

    def test_unsupported(self):
        ok, val = validate_nationality("Atlantis")
        assert ok is False
        assert "not supported" in val.lower()

    def test_substring_match(self):
        ok, val = validate_nationality("Singapore")
        assert ok is True


# ── validate_address ─────────────────────────────────────────


class TestValidateAddress:
    def test_valid_address(self):
        ok, val = validate_address("123 Main St, New York, NY 10001, USA")
        assert ok is True

    def test_too_short(self):
        ok, val = validate_address("123")
        assert ok is False
        assert "too short" in val.lower()

    def test_too_long(self):
        ok, val = validate_address("A" * 501)
        assert ok is False

    def test_strips_whitespace(self):
        ok, val = validate_address("   123 Main Street, City, 12345, Country   ")
        assert ok is True
        assert val.startswith("123")


# ── validate_document_type ───────────────────────────────────


class TestValidateDocumentType:
    @pytest.mark.parametrize("input_val,expected", [
        ("1", "passport"),
        ("passport", "passport"),
        ("护照", "passport"),
        ("2", "national_id"),
        ("身份证", "national_id"),
        ("3", "drivers_license"),
        ("驾照", "drivers_license"),
    ])
    def test_valid_selections(self, input_val, expected):
        ok, val = validate_document_type(input_val)
        assert ok is True
        assert val == expected

    def test_invalid_selection(self):
        ok, val = validate_document_type("potato")
        assert ok is False

    def test_case_insensitive(self):
        ok, val = validate_document_type("PASSPORT")
        assert ok is True


# ── validate_image_meta ──────────────────────────────────────


class TestValidateImageMeta:
    def test_valid_jpeg(self):
        ok, val = validate_image_meta(500_000, "image/jpeg")
        assert ok is True

    def test_too_small(self):
        ok, val = validate_image_meta(50_000, "image/jpeg")
        assert ok is False

    def test_too_large(self):
        ok, val = validate_image_meta(20_000_000, "image/jpeg")
        assert ok is False

    def test_invalid_mime(self):
        ok, val = validate_image_meta(500_000, "application/pdf")
        assert ok is False

    def test_no_mime_check(self):
        ok, val = validate_image_meta(500_000)
        assert ok is True
