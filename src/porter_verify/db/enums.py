"""Controlled vocabularies used across models, services, and the API.

Keeping these as ``StrEnum`` gives us type safety in Python while storing readable
strings in the database. They are the single source of truth for status values.
"""

from __future__ import annotations

from enum import StrEnum


class RegistrationStatus(StrEnum):
    """Normalized registration status, mapped from raw per-state jargon."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DISSOLVED = "dissolved"
    DELINQUENT = "delinquent"
    UNKNOWN = "unknown"


class VerificationStatus(StrEnum):
    """Overall, derived verification outcome shown to users (plan §12.2)."""

    VERIFIED = "verified"
    LIKELY_MATCH = "likely_match"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    INACTIVE_NOT_ELIGIBLE = "inactive_not_eligible"
    RISK_FLAG = "risk_flag"


class RunStatus(StrEnum):
    """Lifecycle state of a single verification run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SOURCE_UNAVAILABLE = "source_unavailable"


class ReviewDecision(StrEnum):
    """A human reviewer's decision on a run/company."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_INFO = "needs_more_info"


class EvidenceType(StrEnum):
    """Kind of stored evidence artifact."""

    SCREENSHOT = "screenshot"
    RAW_JSON = "raw_json"
    PDF = "pdf"


class IdentifierType(StrEnum):
    """Types of external identifiers attached to a company."""

    STATE_REG = "state_reg"  # state registration number
    UEI = "uei"  # SAM.gov Unique Entity ID
    EIN_HASH = "ein_hash"  # salted hash of a claimed EIN (never plaintext)
    DUNS = "duns"
    DOMAIN = "domain"


class SyncStatus(StrEnum):
    """Salesforce sync outcome."""

    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
