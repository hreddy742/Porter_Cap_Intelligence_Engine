"""Human review decisions (immutable once recorded)."""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from porter_verify.db.base import Base, CapturedAtMixin, uuid_pk
from porter_verify.db.enums import ReviewDecision


class ReviewDecisionRecord(Base, CapturedAtMixin):
    """A reviewer's decision on a verification run.

    Immutable: a decision is a historical fact. Changing one's mind creates a new
    record, preserving the full decision trail for audit.
    """

    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = uuid_pk()
    verification_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_runs.id"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision, native_enum=False, length=20), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    # Which candidate the reviewer chose, when disambiguating.
    candidate_chosen: Mapped[str | None] = mapped_column(String(255))
    # Snapshot of status before/after the decision, for the audit trail.
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
