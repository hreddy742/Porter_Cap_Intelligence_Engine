"""UCC search and filing intelligence records."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from porter_verify.db.base import Base, TimestampMixin, uuid_pk
from porter_verify.db.enums import UccSearchOutcome, UccSearchStatus


class UccSearchOrder(Base, TimestampMixin):
    """An exact-name, state-level UCC search and its source-backed outcome."""

    __tablename__ = "ucc_search_orders"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    search_name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[UccSearchStatus] = mapped_column(
        Enum(UccSearchStatus, native_enum=False, length=20),
        default=UccSearchStatus.PENDING,
        nullable=False,
    )
    outcome: Mapped[UccSearchOutcome | None] = mapped_column(
        Enum(UccSearchOutcome, native_enum=False, length=30)
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)
    requested_by_email: Mapped[str] = mapped_column(String(320), nullable=False)
    completed_by_email: Mapped[str | None] = mapped_column(String(320))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UccFiling(Base, TimestampMixin):
    """A normalized UCC filing record from a state source."""

    __tablename__ = "ucc_filings"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    filing_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    filing_type: Mapped[str] = mapped_column(String(30), nullable=False)
    debtor_name: Mapped[str] = mapped_column(String(500), nullable=False)
    debtor_normalized: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    debtor_address: Mapped[str | None] = mapped_column(Text)
    debtor_city: Mapped[str | None] = mapped_column(String(200))
    debtor_state: Mapped[str | None] = mapped_column(String(2))
    debtor_zip: Mapped[str | None] = mapped_column(String(20))
    secured_party_name: Mapped[str | None] = mapped_column(String(500))
    secured_party_normalized: Mapped[str | None] = mapped_column(String(500), index=True)
    collateral_description: Mapped[str | None] = mapped_column(Text)
    filing_date: Mapped[date | None] = mapped_column(Date, index=True)
    termination_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str | None] = mapped_column(String(30))
    lender_type: Mapped[str] = mapped_column(String(30), default="UNKNOWN", nullable=False)
    is_factoring_related: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_mca_related: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_state: Mapped[str | None] = mapped_column(String(2))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    acquisition_method: Mapped[str | None] = mapped_column(String(30))
    search_query: Mapped[str | None] = mapped_column(String(500))
    match_confidence: Mapped[int | None] = mapped_column(Integer)


class KnownFactor(Base):
    """A deterministic watchlist of factoring, MCA, ABL, and bank lenders."""

    __tablename__ = "known_factors"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    lender_type: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    added_by: Mapped[str | None] = mapped_column(String(320))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UccExitSignal(Base):
    """A UCC-3 termination lead signal with evidence links."""

    __tablename__ = "ucc_exit_signals"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    debtor_name: Mapped[str] = mapped_column(String(500), nullable=False)
    debtor_normalized: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    previous_factor: Mapped[str | None] = mapped_column(String(500))
    ucc1_filing_id: Mapped[str | None] = mapped_column(String(100))
    ucc3_filing_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ucc1_date: Mapped[date | None] = mapped_column(Date)
    ucc3_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    days_since_exit: Mapped[int] = mapped_column(Integer, nullable=False)
    replacement_filed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signal_strength: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UccRefreshLog(Base):
    """Append-only log of UCC refresh attempts."""

    __tablename__ = "ucc_refresh_log"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    refresh_type: Mapped[str] = mapped_column(String(20), nullable=False)
    records_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_text: Mapped[str | None] = mapped_column(Text)
