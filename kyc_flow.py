#!/usr/bin/env python3
"""
Binance KYC Flow Controller
Manages the state machine for conversational KYC verification.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

# Session storage directory
SESSIONS_DIR = Path("workspace/kyc-sessions")
UPLOADS_DIR = Path("workspace/kyc-uploads")


class KYCState(Enum):
    AWAITING_CONSENT = "awaiting_consent"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_DOB = "collecting_dob"
    COLLECTING_NATIONALITY = "collecting_nationality"
    COLLECTING_ADDRESS = "collecting_address"
    SELECTING_DOCUMENT = "selecting_document"
    UPLOADING_DOC_FRONT = "uploading_doc_front"
    UPLOADING_DOC_BACK = "uploading_doc_back"
    UPLOADING_SELFIE = "uploading_selfie"
    REVIEWING = "reviewing"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# Countries that require back-of-document photo
SINGLE_SIDE_DOCS = {"passport"}
DOUBLE_SIDE_DOCS = {"national_id", "drivers_license"}

SUPPORTED_COUNTRIES = [
    "United States", "United Kingdom", "Canada", "Australia",
    "Japan", "South Korea", "Singapore", "Hong Kong",
    "Germany", "France", "Netherlands", "Switzerland",
    "Brazil", "Mexico", "Argentina",
    "India", "Indonesia", "Philippines", "Vietnam",
    "UAE", "Saudi Arabia", "Turkey",
    "Russia", "Ukraine", "China",
]

DOCUMENT_TYPES = {
    "1": "passport",
    "passport": "passport",
    "护照": "passport",
    "2": "national_id",
    "national id": "national_id",
    "id": "national_id",
    "id card": "national_id",
    "身份证": "national_id",
    "3": "drivers_license",
    "driver's license": "drivers_license",
    "drivers license": "drivers_license",
    "driving license": "drivers_license",
    "驾照": "drivers_license",
    "驾驶证": "drivers_license",
}

DOCUMENT_LABELS = {
    "passport": "🛂 Passport",
    "national_id": "🪪 National ID Card",
    "drivers_license": "🚗 Driver's License",
}


def create_session(user_id: str) -> dict:
    """Create a new KYC session for a user."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    session = {
        "session_id": f"KYC-2026-{uuid.uuid4().hex[:5].upper()}",
        "user_id": user_id,
        "state": KYCState.AWAITING_CONSENT.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "language": "en",
        "personal_info": {
            "full_name": None,
            "date_of_birth": None,
            "nationality": None,
            "address": None,
        },
        "document": {
            "type": None,
            "front_image": None,
            "back_image": None,
        },
        "selfie": {
            "image": None,
        },
        "verification": {
            "status": "pending",
            "submitted_at": None,
            "result": None,
            "rejection_reason": None,
        },
    }
    
    save_session(user_id, session)
    return session


def load_session(user_id: str) -> dict | None:
    """Load an existing session for a user."""
    path = SESSIONS_DIR / f"{user_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_session(user_id: str, session: dict):
    """Save session state."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = SESSIONS_DIR / f"{user_id}.json"
    path.write_text(json.dumps(session, indent=2, ensure_ascii=False))


def delete_session(user_id: str):
    """Delete a user's session data."""
    path = SESSIONS_DIR / f"{user_id}.json"
    if path.exists():
        path.unlink()
    # Also clean up uploaded files
    user_uploads = UPLOADS_DIR / user_id
    if user_uploads.exists():
        import shutil
        shutil.rmtree(user_uploads)


def validate_name(name: str) -> tuple[bool, str]:
    """Validate a full legal name."""
    name = name.strip()
    if len(name) < 2:
        return False, "Name is too short. Please enter your full legal name."
    if len(name) > 100:
        return False, "Name is too long. Please keep it under 100 characters."
    return True, name


def validate_dob(dob_str: str) -> tuple[bool, str]:
    """Validate date of birth. Must be 18+."""
    from dateutil.parser import parse as parse_date
    try:
        dob = parse_date(dob_str).date()
    except (ValueError, ImportError):
        # Fallback without dateutil
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y.%m.%d", "%d-%m-%Y"):
            try:
                dob = datetime.strptime(dob_str.strip(), fmt).date()
                break
            except ValueError:
                continue
        else:
            return False, "Invalid date format. Please use YYYY-MM-DD (e.g., 1990-01-15)."
    
    today = datetime.now(timezone.utc).date()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    if age < 18:
        return False, "You must be at least 18 years old to complete KYC verification."
    if age > 120:
        return False, "Please enter a valid date of birth."
    
    return True, dob.isoformat()


def validate_nationality(nationality: str) -> tuple[bool, str]:
    """Validate nationality against supported countries."""
    nationality = nationality.strip().title()
    
    # Fuzzy match
    for country in SUPPORTED_COUNTRIES:
        if nationality.lower() in country.lower() or country.lower() in nationality.lower():
            return True, country
    
    return False, f"Sorry, '{nationality}' is not in our supported regions. Supported: {', '.join(SUPPORTED_COUNTRIES[:5])}..."


def get_next_state(current_state: str, doc_type: str = None) -> str:
    """Determine the next state in the flow."""
    transitions = {
        KYCState.AWAITING_CONSENT.value: KYCState.COLLECTING_NAME.value,
        KYCState.COLLECTING_NAME.value: KYCState.COLLECTING_DOB.value,
        KYCState.COLLECTING_DOB.value: KYCState.COLLECTING_NATIONALITY.value,
        KYCState.COLLECTING_NATIONALITY.value: KYCState.COLLECTING_ADDRESS.value,
        KYCState.COLLECTING_ADDRESS.value: KYCState.SELECTING_DOCUMENT.value,
        KYCState.SELECTING_DOCUMENT.value: KYCState.UPLOADING_DOC_FRONT.value,
        KYCState.UPLOADING_DOC_FRONT.value: (
            KYCState.UPLOADING_SELFIE.value 
            if doc_type in SINGLE_SIDE_DOCS 
            else KYCState.UPLOADING_DOC_BACK.value
        ),
        KYCState.UPLOADING_DOC_BACK.value: KYCState.UPLOADING_SELFIE.value,
        KYCState.UPLOADING_SELFIE.value: KYCState.REVIEWING.value,
        KYCState.REVIEWING.value: KYCState.SUBMITTED.value,
    }
    return transitions.get(current_state)


def get_state_prompt(state: str, session: dict, lang: str = "en") -> str:
    """Get the prompt message for a given state."""
    prompts = {
        KYCState.AWAITING_CONSENT.value: (
            "👋 Welcome to Binance Identity Verification!\n\n"
            "To use Binance services, we need to verify your identity. "
            "This process takes about 5 minutes.\n\n"
            "You'll need:\n"
            "📄 A valid government-issued ID (passport, national ID, or driver's license)\n"
            "📸 A clear selfie\n"
            "📍 Your current residential address\n\n"
            "Your data is encrypted and handled per our Privacy Policy.\n\n"
            "Do you agree to proceed? (Yes / No)"
        ),
        KYCState.COLLECTING_NAME.value: (
            "Great! Let's start. 📝\n\n"
            "What is your **full legal name** as it appears on your ID document?"
        ),
        KYCState.COLLECTING_DOB.value: (
            "📅 What is your **date of birth**?\n"
            "(Format: YYYY-MM-DD, e.g., 1990-01-15)"
        ),
        KYCState.COLLECTING_NATIONALITY.value: (
            "🌍 What is your **nationality/country of citizenship**?"
        ),
        KYCState.COLLECTING_ADDRESS.value: (
            "📍 What is your **current residential address**?\n"
            "(Include street, city, postal code, and country)"
        ),
        KYCState.SELECTING_DOCUMENT.value: (
            "Please select your ID document type:\n\n"
            "1️⃣ Passport\n"
            "2️⃣ National ID Card\n"
            "3️⃣ Driver's License\n\n"
            "Reply with the number or name."
        ),
        KYCState.UPLOADING_DOC_FRONT.value: (
            f"📄 Please send a clear photo of the **front** of your "
            f"{DOCUMENT_LABELS.get(session.get('document', {}).get('type', ''), 'document')}.\n\n"
            "Tips for a good photo:\n"
            "✅ Place on a flat, dark surface\n"
            "✅ Ensure good lighting\n"
            "✅ All 4 corners must be visible\n"
            "✅ No glare or blur"
        ),
        KYCState.UPLOADING_DOC_BACK.value: (
            "Now please send a clear photo of the **back** of your document."
        ),
        KYCState.UPLOADING_SELFIE.value: (
            "📸 Almost done! Please send a **selfie** of yourself.\n\n"
            "Tips:\n"
            "✅ Face the camera directly\n"
            "✅ Good lighting, no shadows\n"
            "✅ No sunglasses or masks\n"
            "✅ Match your ID photo"
        ),
        KYCState.REVIEWING.value: _build_review_message(session),
        KYCState.SUBMITTED.value: (
            f"✅ Your verification has been submitted!\n\n"
            f"⏳ Processing usually takes 1-3 business days.\n"
            f"We'll notify you as soon as your verification is complete.\n\n"
            f"📋 Reference ID: **{session.get('session_id', 'N/A')}**"
        ),
    }
    return prompts.get(state, "Unknown state. Please type /start_kyc to begin again.")


def _build_review_message(session: dict) -> str:
    """Build the review summary message."""
    pi = session.get("personal_info", {})
    doc = session.get("document", {})
    selfie = session.get("selfie", {})
    
    doc_status = "✅ Uploaded" if doc.get("front_image") else "❌ Missing"
    back_status = ""
    if doc.get("type") in DOUBLE_SIDE_DOCS:
        back_status = f"\n   Back: {'✅' if doc.get('back_image') else '❌'}"
    selfie_status = "✅ Uploaded" if selfie.get("image") else "❌ Missing"
    
    return (
        "📋 **Please review your information:**\n\n"
        f"👤 Name: {pi.get('full_name', 'N/A')}\n"
        f"📅 DOB: {pi.get('date_of_birth', 'N/A')}\n"
        f"🌍 Nationality: {pi.get('nationality', 'N/A')}\n"
        f"📍 Address: {pi.get('address', 'N/A')}\n\n"
        f"📄 Document: {DOCUMENT_LABELS.get(doc.get('type', ''), 'N/A')}\n"
        f"   Front: {doc_status}{back_status}\n"
        f"📸 Selfie: {selfie_status}\n\n"
        "Is everything correct? Reply **Confirm** to submit, or **Edit** to make changes."
    )


if __name__ == "__main__":
    # Quick test
    session = create_session("test_user_123")
    print(f"Created session: {session['session_id']}")
    print(f"State: {session['state']}")
    print(f"\nWelcome message:\n{get_state_prompt(session['state'], session)}")
    
    # Advance state
    session["state"] = get_next_state(session["state"])
    print(f"\nNext state: {session['state']}")
    print(f"Prompt:\n{get_state_prompt(session['state'], session)}")
