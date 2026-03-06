#!/usr/bin/env python3
"""
Input validators for Binance KYC flow.
"""

import re
from datetime import datetime, timezone


def validate_name(name: str) -> tuple[bool, str]:
    """
    Validate full legal name.
    Returns (is_valid, cleaned_name_or_error_message)
    """
    name = name.strip()
    
    if not name:
        return False, "Please enter your full legal name."
    
    if len(name) < 2:
        return False, "Name is too short. Please enter your full legal name as it appears on your ID."
    
    if len(name) > 100:
        return False, "Name is too long (max 100 characters)."
    
    # Allow letters, spaces, hyphens, apostrophes, dots, and Unicode chars
    # This is intentionally permissive to support international names
    if re.match(r'^[\d!@#$%^&*()+=\[\]{}|\\:;"<>,?/]+$', name):
        return False, "That doesn't look like a valid name. Please enter your full legal name."
    
    return True, name


def validate_date_of_birth(dob_str: str) -> tuple[bool, str]:
    """
    Validate date of birth. Must be 18+.
    Supports formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, YYYY.MM.DD
    Returns (is_valid, iso_date_or_error_message)
    """
    dob_str = dob_str.strip()
    
    formats = [
        "%Y-%m-%d",      # 1990-01-15
        "%Y/%m/%d",      # 1990/01/15
        "%d/%m/%Y",      # 15/01/1990
        "%d-%m-%Y",      # 15-01-1990
        "%Y.%m.%d",      # 1990.01.15
        "%d.%m.%Y",      # 15.01.1990
        "%B %d, %Y",     # January 15, 1990
        "%b %d, %Y",     # Jan 15, 1990
    ]
    
    dob = None
    for fmt in formats:
        try:
            dob = datetime.strptime(dob_str, fmt).date()
            break
        except ValueError:
            continue
    
    if dob is None:
        return False, "Invalid date format. Please use YYYY-MM-DD (e.g., 1990-01-15)."
    
    today = datetime.now(timezone.utc).date()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    if age < 18:
        return False, "You must be at least 18 years old to complete KYC verification."
    
    if age > 120:
        return False, "Please enter a valid date of birth."
    
    if dob > today:
        return False, "Date of birth cannot be in the future."
    
    return True, dob.isoformat()


def validate_nationality(nationality: str, supported_countries: list[str]) -> tuple[bool, str]:
    """
    Validate nationality against supported countries list.
    Returns (is_valid, matched_country_or_error_message)
    """
    nationality = nationality.strip()
    
    if not nationality:
        return False, "Please enter your nationality or country of citizenship."
    
    # Common nationality-to-country mappings
    nationality_map = {
        "american": "United States",
        "us": "United States",
        "usa": "United States",
        "british": "United Kingdom",
        "uk": "United Kingdom",
        "canadian": "Canada",
        "australian": "Australia",
        "japanese": "Japan",
        "korean": "South Korea",
        "south korean": "South Korea",
        "singaporean": "Singapore",
        "german": "Germany",
        "french": "France",
        "dutch": "Netherlands",
        "swiss": "Switzerland",
        "brazilian": "Brazil",
        "mexican": "Mexico",
        "argentine": "Argentina",
        "argentinian": "Argentina",
        "indian": "India",
        "indonesian": "Indonesia",
        "filipino": "Philippines",
        "vietnamese": "Vietnam",
        "emirati": "UAE",
        "saudi": "Saudi Arabia",
        "turkish": "Turkey",
        "russian": "Russia",
        "ukrainian": "Ukraine",
        "chinese": "China",
        "中国": "China",
        "中国人": "China",
        "日本": "Japan",
        "日本人": "Japan",
        "한국": "South Korea",
    }
    
    # Direct match
    lower = nationality.lower()
    if lower in nationality_map:
        country = nationality_map[lower]
        if country in supported_countries:
            return True, country
    
    # Fuzzy match against country names
    for country in supported_countries:
        if lower == country.lower():
            return True, country
        if lower in country.lower() or country.lower() in lower:
            return True, country
    
    return False, (
        f"Sorry, '{nationality}' is not currently supported for verification.\n"
        f"Supported regions include: {', '.join(supported_countries[:10])}..."
    )


def validate_address(address: str) -> tuple[bool, str]:
    """
    Validate residential address.
    Returns (is_valid, cleaned_address_or_error_message)
    """
    address = address.strip()
    
    if not address:
        return False, "Please enter your residential address."
    
    if len(address) < 10:
        return False, "Address seems too short. Please include street, city, postal code, and country."
    
    if len(address) > 500:
        return False, "Address is too long. Please keep it under 500 characters."
    
    return True, address


def validate_document_type(input_str: str) -> tuple[bool, str]:
    """
    Validate and normalize document type selection.
    Returns (is_valid, document_type_key_or_error_message)
    """
    doc_map = {
        "1": "passport",
        "passport": "passport",
        "护照": "passport",
        "パスポート": "passport",
        "여권": "passport",
        "2": "national_id",
        "national id": "national_id",
        "national id card": "national_id",
        "id": "national_id",
        "id card": "national_id",
        "身份证": "national_id",
        "マイナンバーカード": "national_id",
        "신분증": "national_id",
        "3": "drivers_license",
        "driver's license": "drivers_license",
        "drivers license": "drivers_license",
        "driving license": "drivers_license",
        "license": "drivers_license",
        "驾照": "drivers_license",
        "驾驶证": "drivers_license",
        "運転免許証": "drivers_license",
        "운전면허증": "drivers_license",
    }
    
    lower = input_str.strip().lower()
    
    if lower in doc_map:
        return True, doc_map[lower]
    
    return False, (
        "Please select a valid document type:\n"
        "1️⃣ Passport\n"
        "2️⃣ National ID Card\n"
        "3️⃣ Driver's License"
    )


def validate_image_metadata(file_size_bytes: int, mime_type: str = None) -> tuple[bool, str]:
    """
    Validate image metadata (size, format).
    Actual image quality checks would be done server-side in production.
    Returns (is_valid, error_message_or_empty)
    """
    min_size = 100 * 1024       # 100 KB
    max_size = 10 * 1024 * 1024  # 10 MB
    
    allowed_types = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
    
    if file_size_bytes < min_size:
        return False, "Image is too small. Please send a higher resolution photo."
    
    if file_size_bytes > max_size:
        return False, "Image is too large (max 10MB). Please send a smaller file."
    
    if mime_type and mime_type not in allowed_types:
        return False, f"Unsupported image format. Please send a JPG or PNG image."
    
    return True, ""


def detect_language(text: str) -> str:
    """
    Simple language detection based on character ranges.
    Returns ISO language code.
    """
    # Check for CJK characters
    if re.search(r'[\u4e00-\u9fff]', text):
        return "zh"
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return "ja"
    if re.search(r'[\uac00-\ud7af]', text):
        return "ko"
    if re.search(r'[\u0400-\u04ff]', text):
        return "ru"
    if re.search(r'[\u0600-\u06ff]', text):
        return "ar"
    
    return "en"
