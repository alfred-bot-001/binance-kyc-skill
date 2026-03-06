"""Input validators for every step of the KYC flow.

Each validator returns ``(ok, value_or_error)`` where *value* is the
cleaned/normalised input on success, or a user-friendly error message
on failure.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import NamedTuple

from binance_kyc.models.enums import DocumentType


class ValidationResult(NamedTuple):
    """Result of a single validation check."""

    ok: bool
    value: str


# ── Supported countries ──────────────────────────────────────

SUPPORTED_COUNTRIES: list[str] = [
    "Argentina", "Australia", "Brazil", "Canada", "China",
    "France", "Germany", "Hong Kong", "India", "Indonesia",
    "Japan", "Mexico", "Netherlands", "Philippines",
    "Russia", "Saudi Arabia", "Singapore", "South Korea",
    "Switzerland", "Turkey", "UAE", "Ukraine",
    "United Kingdom", "United States", "Vietnam",
]

_NATIONALITY_MAP: dict[str, str] = {
    "american": "United States", "us": "United States", "usa": "United States",
    "british": "United Kingdom", "uk": "United Kingdom",
    "canadian": "Canada", "australian": "Australia",
    "japanese": "Japan", "korean": "South Korea", "south korean": "South Korea",
    "singaporean": "Singapore", "german": "Germany",
    "french": "France", "dutch": "Netherlands", "swiss": "Switzerland",
    "brazilian": "Brazil", "mexican": "Mexico",
    "argentine": "Argentina", "argentinian": "Argentina",
    "indian": "India", "indonesian": "Indonesia",
    "filipino": "Philippines", "vietnamese": "Vietnam",
    "emirati": "UAE", "saudi": "Saudi Arabia", "turkish": "Turkey",
    "russian": "Russia", "ukrainian": "Ukraine",
    "chinese": "China",
    "中国": "China", "中国人": "China",
    "日本": "Japan", "日本人": "Japan",
    "한국": "South Korea",
}

# ── Document type aliases ────────────────────────────────────

_DOC_TYPE_ALIASES: dict[str, DocumentType] = {
    "1": DocumentType.PASSPORT, "passport": DocumentType.PASSPORT,
    "护照": DocumentType.PASSPORT, "パスポート": DocumentType.PASSPORT,
    "여권": DocumentType.PASSPORT,
    "2": DocumentType.NATIONAL_ID, "national id": DocumentType.NATIONAL_ID,
    "national id card": DocumentType.NATIONAL_ID, "id": DocumentType.NATIONAL_ID,
    "id card": DocumentType.NATIONAL_ID,
    "身份证": DocumentType.NATIONAL_ID,
    "3": DocumentType.DRIVERS_LICENSE, "driver's license": DocumentType.DRIVERS_LICENSE,
    "drivers license": DocumentType.DRIVERS_LICENSE,
    "driving license": DocumentType.DRIVERS_LICENSE, "license": DocumentType.DRIVERS_LICENSE,
    "驾照": DocumentType.DRIVERS_LICENSE, "驾驶证": DocumentType.DRIVERS_LICENSE,
}

# ── Date formats ─────────────────────────────────────────────

_DATE_FORMATS: list[str] = [
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y",
    "%Y.%m.%d", "%d.%m.%Y", "%B %d, %Y", "%b %d, %Y",
]


# ── Validators ───────────────────────────────────────────────

def validate_name(raw: str) -> ValidationResult:
    """Validate a full legal name."""
    name = raw.strip()
    if len(name) < 2:
        return ValidationResult(False, "Name is too short. Please enter your full legal name.")
    if len(name) > 100:
        return ValidationResult(False, "Name is too long (max 100 characters).")
    if re.fullmatch(r'[\d!@#$%^&*()+=\[\]{}|\\:;"<>,?/]+', name):
        return ValidationResult(False, "That doesn't look like a name. Please try again.")
    return ValidationResult(True, name)


def validate_date_of_birth(raw: str) -> ValidationResult:
    """Validate date of birth — user must be at least 18."""
    text = raw.strip()
    dob = None
    for fmt in _DATE_FORMATS:
        try:
            dob = datetime.strptime(text, fmt).date()
            break
        except ValueError:
            continue
    if dob is None:
        return ValidationResult(False, "Invalid date. Please use YYYY-MM-DD (e.g. 1990-01-15).")

    today = datetime.now(UTC).date()
    if dob > today:
        return ValidationResult(False, "Date of birth cannot be in the future.")
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18:
        return ValidationResult(False, "You must be at least 18 years old.")
    if age > 120:
        return ValidationResult(False, "Please enter a valid date of birth.")
    return ValidationResult(True, dob.isoformat())


def validate_nationality(raw: str) -> ValidationResult:
    """Match user input to a supported country."""
    text = raw.strip()
    lower = text.lower()

    # Exact alias
    if lower in _NATIONALITY_MAP:
        country = _NATIONALITY_MAP[lower]
        if country in SUPPORTED_COUNTRIES:
            return ValidationResult(True, country)

    # Substring match
    for country in SUPPORTED_COUNTRIES:
        if lower == country.lower() or lower in country.lower():
            return ValidationResult(True, country)

    top = ", ".join(SUPPORTED_COUNTRIES[:8])
    return ValidationResult(False, f"'{text}' is not supported. Supported: {top}…")


def validate_address(raw: str) -> ValidationResult:
    """Validate a residential address (basic length check)."""
    addr = raw.strip()
    if len(addr) < 10:
        return ValidationResult(False, "Address is too short. Include street, city, postal code, country.")
    if len(addr) > 500:
        return ValidationResult(False, "Address is too long (max 500 characters).")
    return ValidationResult(True, addr)


def validate_document_type(raw: str) -> ValidationResult:
    """Normalise document type selection."""
    key = raw.strip().lower()
    doc = _DOC_TYPE_ALIASES.get(key)
    if doc is not None:
        return ValidationResult(True, doc.value)
    return ValidationResult(
        False,
        "Please choose:\n1️⃣ Passport\n2️⃣ National ID Card\n3️⃣ Driver's License",
    )


def validate_image_meta(size_bytes: int, mime: str | None = None) -> ValidationResult:
    """Check image size and MIME type."""
    if size_bytes < 100 * 1024:
        return ValidationResult(False, "Image too small. Please send a higher-resolution photo.")
    if size_bytes > 10 * 1024 * 1024:
        return ValidationResult(False, "Image too large (max 10 MB).")
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if mime and mime not in allowed:
        return ValidationResult(False, "Unsupported format. Please send JPG or PNG.")
    return ValidationResult(True, "")
