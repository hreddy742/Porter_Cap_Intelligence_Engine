"""Source staging tables.

Open-data sources (e.g. Colorado) are ingested into a per-source staging table that
the connector queries. This keeps the acquisition (bulk download → staging) separate
from verification: a verify run still searches the connector and produces a company
with its own evidence + audit, exactly like any live source. Staging is a cache of
the source, NOT the canonical company spine.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import JSON, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from porter_verify.db.base import Base, TimestampMixin


class CtBusinessEntity(Base, TimestampMixin):
    """One ingested Connecticut business-entity record (keyed by account number)."""

    __tablename__ = "ct_business_entities"

    entity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    entity_name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    status_raw: Mapped[str | None] = mapped_column(String(200))
    entity_type: Mapped[str | None] = mapped_column(String(100))
    formation_date: Mapped[date | None] = mapped_column(Date, index=True)
    principal_address: Mapped[str | None] = mapped_column(Text)
    mailing_address: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(String(100))
    source_record_url: Mapped[str | None] = mapped_column(String(1000))
    agent_name: Mapped[str | None] = mapped_column(String(300))
    agent_address: Mapped[str | None] = mapped_column(Text)
    officers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    raw: Mapped[dict] = mapped_column(JSON, nullable=False)


class OrBusinessEntity(Base, TimestampMixin):
    """One ingested Oregon business-entity record (keyed by registry number)."""

    __tablename__ = "or_business_entities"

    entity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    entity_name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    status_raw: Mapped[str | None] = mapped_column(String(200))
    entity_type: Mapped[str | None] = mapped_column(String(100))
    formation_date: Mapped[date | None] = mapped_column(Date, index=True)
    principal_address: Mapped[str | None] = mapped_column(Text)
    mailing_address: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(String(100))
    source_record_url: Mapped[str | None] = mapped_column(String(1000))
    agent_name: Mapped[str | None] = mapped_column(String(300))
    agent_address: Mapped[str | None] = mapped_column(Text)
    officers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    raw: Mapped[dict] = mapped_column(JSON, nullable=False)


class CoBusinessEntity(Base, TimestampMixin):
    """One ingested Colorado business-entity record (keyed by the state's entity id)."""

    __tablename__ = "co_business_entities"

    # Colorado's own entity id is the natural primary key (stable, unique).
    entity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    entity_name: Mapped[str] = mapped_column(String(500), nullable=False)
    # Normalized for fast name search (same normalization as everything else).
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    status_raw: Mapped[str | None] = mapped_column(String(200))
    entity_type: Mapped[str | None] = mapped_column(String(100))
    formation_date: Mapped[date | None] = mapped_column(Date, index=True)
    principal_address: Mapped[str | None] = mapped_column(Text)
    mailing_address: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(String(100))
    source_record_url: Mapped[str | None] = mapped_column(String(1000))
    agent_name: Mapped[str | None] = mapped_column(String(300))
    agent_address: Mapped[str | None] = mapped_column(Text)
    officers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Full verbatim CSV row, so nothing is lost before normalization.
    raw: Mapped[dict] = mapped_column(JSON, nullable=False)


class OhBusinessEntity(Base, TimestampMixin):
    """One ingested Ohio business-entity record (keyed by charter number)."""

    __tablename__ = "oh_business_entities"

    entity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    entity_name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    status_raw: Mapped[str | None] = mapped_column(String(200))
    entity_type: Mapped[str | None] = mapped_column(String(100))
    formation_date: Mapped[date | None] = mapped_column(Date, index=True)
    principal_address: Mapped[str | None] = mapped_column(Text)
    mailing_address: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(String(100))
    source_record_url: Mapped[str | None] = mapped_column(String(1000))
    agent_name: Mapped[str | None] = mapped_column(String(300))
    agent_address: Mapped[str | None] = mapped_column(Text)
    officers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    raw: Mapped[dict] = mapped_column(JSON, nullable=False)
