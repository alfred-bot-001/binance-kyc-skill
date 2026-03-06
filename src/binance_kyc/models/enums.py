"""Enumerations used throughout the KYC flow."""

from __future__ import annotations

from enum import StrEnum


class KYCState(StrEnum):
    """All possible states in the KYC verification flow.

    Flow: consent → personal info → document upload → review
          → liveness (browser redirect) → submitted → approved/rejected
    """

    AWAITING_CONSENT = "awaiting_consent"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_DOB = "collecting_dob"
    COLLECTING_NATIONALITY = "collecting_nationality"
    COLLECTING_ADDRESS = "collecting_address"
    SELECTING_DOCUMENT = "selecting_document"
    UPLOADING_DOC_FRONT = "uploading_doc_front"
    UPLOADING_DOC_BACK = "uploading_doc_back"
    REVIEWING = "reviewing"
    AWAITING_LIVENESS = "awaiting_liveness"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class DocumentType(StrEnum):
    """Supported identity document types."""

    PASSPORT = "passport"
    NATIONAL_ID = "national_id"
    DRIVERS_LICENSE = "drivers_license"


class VerificationStatus(StrEnum):
    """Verification processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"


class LivenessStatus(StrEnum):
    """Liveness check status."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"


# Document types that only need a front photo
SINGLE_SIDE_DOCUMENTS: frozenset[DocumentType] = frozenset({DocumentType.PASSPORT})

# Document types that need both front and back photos
DOUBLE_SIDE_DOCUMENTS: frozenset[DocumentType] = frozenset({
    DocumentType.NATIONAL_ID,
    DocumentType.DRIVERS_LICENSE,
})
