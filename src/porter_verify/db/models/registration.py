"""Per-state registrations, registered agents, and officers.

These carry both the raw state status and the normalized status, and always
reference the source that produced them (provenance).
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from porter_verify.db.base import Base, CapturedAtMixin, TimestampMixin, uuid_pk
from porter_verify.db.enums import RegistrationStatus


class BusinessRegistration(Base, TimestampMixin):
    """A company's registration in a specific state."""

    __tablename__ = "business_registrations"
    __table_args__ = (UniqueConstraint("state", "state_entity_id", name="state_entity"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    state_entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    formation_date: Mapped[date | None] = mapped_column(Date)
    # Raw state jargon kept verbatim alongside the normalized value.
    status_raw: Mapped[str | None] = mapped_column(String(200))
    status_normalized: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, native_enum=False, length=20),
        default=RegistrationStatus.UNKNOWN,
        nullable=False,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_registry.id"))

    agents: Mapped[list[RegisteredAgent]] = relationship(
        back_populates="registration", cascade="all, delete-orphan"
    )


class RegisteredAgent(Base, CapturedAtMixin):
    """A registered agent on a state registration (PII-adjacent: access-controlled)."""

    __tablename__ = "registered_agents"

    id: Mapped[uuid.UUID] = uuid_pk()
    registration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_registrations.id"), nullable=False
    )
    agent_name: Mapped[str | None] = mapped_column(String(300))
    agent_address: Mapped[str | None] = mapped_column(String(500))
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_registry.id"))

    registration: Mapped[BusinessRegistration] = relationship(back_populates="agents")


class CompanyOfficer(Base, CapturedAtMixin):
    """An officer/principal of a company (PII: restricted role, retention-limited)."""

    __tablename__ = "company_officers"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    title: Mapped[str | None] = mapped_column(String(150))
    address: Mapped[str | None] = mapped_column(String(500))
    # Result of OFAC screening for this officer (None = not yet screened).
    screened_ofac: Mapped[bool | None] = mapped_column(Boolean)
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_registry.id"))
