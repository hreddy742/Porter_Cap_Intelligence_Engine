"""The canonical company spine and its external identifiers."""

from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from porter_verify.db.base import Base, TimestampMixin, uuid_pk
from porter_verify.db.enums import IdentifierType, RegistrationStatus


class Company(Base, TimestampMixin):
    """A canonical, resolved business entity — the spine of the data model.

    Companies are deduplicated via ``dedupe_key`` (home_state|normalized_name) and
    merged only through reviewed, history-preserving merges — never auto-merged on
    fuzzy name alone.
    """

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = uuid_pk()
    canonical_legal_name: Mapped[str] = mapped_column(String(500), nullable=False)
    # Lowercased, punctuation-stripped, suffix-canonicalized name for matching.
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    home_state: Mapped[str | None] = mapped_column(String(2))
    status_normalized: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, native_enum=False, length=20),
        default=RegistrationStatus.UNKNOWN,
        nullable=False,
    )
    entity_age_days: Mapped[int | None] = mapped_column(Integer)
    # home_state|normalized_name — unique to prevent accidental duplicates.
    dedupe_key: Mapped[str] = mapped_column(String(550), unique=True, nullable=False)

    identifiers: Mapped[list[CompanyIdentifier]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class CompanyIdentifier(Base, TimestampMixin):
    """An external identifier for a company (state reg #, UEI, EIN hash, ...)."""

    __tablename__ = "company_identifiers"
    __table_args__ = (UniqueConstraint("id_type", "id_value", name="id_type_value"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    id_type: Mapped[IdentifierType] = mapped_column(
        Enum(IdentifierType, native_enum=False, length=20), nullable=False
    )
    id_value: Mapped[str] = mapped_column(String(255), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_registry.id"))

    company: Mapped[Company] = relationship(back_populates="identifiers")
