"""Shared pytest fixtures.

The ``db_session`` fixture builds an isolated in-memory SQLite database with the
full schema created from the ORM metadata, so model/constraint tests run instantly
without Docker or Postgres. Each test gets a fresh database.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from porter_verify.db import models  # noqa: F401  (registers all tables on metadata)
from porter_verify.db.base import Base


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    """A fresh in-memory SQLite engine with foreign keys enabled and schema created."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """A transactional session bound to the in-memory engine."""

    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
