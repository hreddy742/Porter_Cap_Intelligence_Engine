"""SQLAlchemy declarative base, shared column types, and common mixins.

Design choices for portability (the test suite runs on SQLite, production on
PostgreSQL):
- UUID primary keys use SQLAlchemy's ``Uuid`` type (native uuid on PG, CHAR(32)
  on SQLite).
- Status enums use ``Enum(..., native_enum=False)`` so they become VARCHAR + a
  CHECK constraint, which works on every dialect.
- Timestamps are timezone-aware and default to UTC at insert time.

A constraint naming convention is set so Alembic generates stable, predictable
constraint names across dialects.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Predictable constraint names — important for migrations and debugging.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    """Timezone-aware current UTC time (used as a column default)."""

    return datetime.now(UTC)


def uuid_pk() -> Mapped[uuid.UUID]:
    """A UUID primary key column with a Python-generated default."""

    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` audit timestamps to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class CapturedAtMixin:
    """Adds an immutable ``captured_at`` timestamp for append-only fact rows."""

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
