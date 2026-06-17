"""FastAPI dependencies: database session, connector registry, evidence store.

These are provided via ``app.state`` so tests can override them with an isolated
database and a temp evidence directory. The registry and store are process-wide
singletons created at startup.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.services.evidence import EvidenceStore


def get_session(request: Request) -> Iterator[Session]:
    """Yield a request-scoped DB session from the app's session factory."""

    factory: sessionmaker[Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_registry(request: Request) -> ConnectorRegistry:
    return request.app.state.registry


def get_evidence_store(request: Request) -> EvidenceStore:
    return request.app.state.evidence_store
