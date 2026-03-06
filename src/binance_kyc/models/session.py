"""Session data model — represents one user's KYC verification attempt."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from binance_kyc.models.enums import DocumentType, KYCState, VerificationStatus


class PersonalInfo(BaseModel):
    """User's personal identity information."""

    full_name: str | None = None
    date_of_birth: str | None = None
    nationality: str | None = None
    address: str | None = None


class DocumentInfo(BaseModel):
    """Uploaded identity document metadata."""

    doc_type: DocumentType | None = None
    front_image_path: str | None = None
    back_image_path: str | None = None


class SelfieInfo(BaseModel):
    """Uploaded selfie metadata."""

    image_path: str | None = None


class Verification(BaseModel):
    """Verification result tracking."""

    status: VerificationStatus = VerificationStatus.PENDING
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    result: str | None = None
    rejection_reason: str | None = None


def _generate_reference_id() -> str:
    """Generate a human-readable KYC reference ID."""
    short = uuid.uuid4().hex[:6].upper()
    return f"KYC-{datetime.now(UTC).strftime('%Y%m%d')}-{short}"


class Session(BaseModel):
    """Complete KYC session for a single user.

    This is the root model that gets persisted as JSON per user.
    """

    session_id: str = Field(default_factory=_generate_reference_id)
    user_id: str
    state: KYCState = KYCState.AWAITING_CONSENT
    language: str = "en"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    document: DocumentInfo = Field(default_factory=DocumentInfo)
    selfie: SelfieInfo = Field(default_factory=SelfieInfo)
    verification: Verification = Field(default_factory=Verification)

    def touch(self) -> None:
        """Update the ``updated_at`` timestamp."""
        self.updated_at = datetime.now(UTC)

    def advance_to(self, state: KYCState) -> None:
        """Transition to a new state and bump timestamp."""
        self.state = state
        self.touch()

    @property
    def is_terminal(self) -> bool:
        """Whether the session is in a final state."""
        return self.state in {
            KYCState.APPROVED,
            KYCState.REJECTED,
            KYCState.CANCELLED,
        }

    @property
    def needs_doc_back(self) -> bool:
        """Whether the selected document type requires a back photo."""
        from binance_kyc.models.enums import DOUBLE_SIDE_DOCUMENTS
        return self.document.doc_type in DOUBLE_SIDE_DOCUMENTS
