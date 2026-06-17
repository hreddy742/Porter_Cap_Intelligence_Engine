"""Database engine and session management.

A single engine is created per process from ``settings.database_url``. The
``session_scope`` context manager and the ``get_session`` FastAPI dependency both
yield a session that commits on success and rolls back on error.

SQLite (used by the test suite) needs special handling: an in-memory database must
share one connection across the app, and foreign-key enforcement must be turned on
explicitly.
"""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from porter_verify.config import Settings, get_settings


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def create_db_engine(settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine appropriate for the configured database."""

    settings = settings or get_settings()
    url = settings.database_url

    if _is_sqlite(url):
        # Share one connection for in-memory SQLite so all sessions see the same
        # data; enable cross-thread use for the test client.
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if ":memory:" in url else None,
        )

        # SQLite needs foreign keys turned on, and a busy timeout so concurrent
        # background verifications wait for the write lock instead of erroring with
        # "database is locked".
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        return engine

    # PostgreSQL (and others): standard pooled engine.
    return create_engine(url, pool_pre_ping=True)


# Default process-wide engine + session factory.
engine: Engine = create_db_engine()
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False
)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commit on success, roll back on error, always close."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped session."""

    with session_scope() as session:
        yield session
