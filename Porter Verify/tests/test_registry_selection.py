"""Tests that the default registry selects the right connector per state.

Colorado must win for CO (real data); the nationwide mock handles everything else.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from porter_verify.connectors.base import CAP_STATUS
from porter_verify.connectors.factory import build_default_registry
from porter_verify.db import models  # noqa: F401
from porter_verify.db.base import Base


def _factory() -> sessionmaker:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)  # CO connector's health() needs its table
    return sessionmaker(bind=engine)


def test_colorado_connector_wins_for_co() -> None:
    registry = build_default_registry(_factory())
    chosen = registry.select(state="CO", capability=CAP_STATUS)
    assert chosen is not None
    assert chosen.name == "colorado_sos_opendata"


def test_mock_handles_other_states() -> None:
    registry = build_default_registry(_factory())
    chosen = registry.select(state="TX", capability=CAP_STATUS)
    assert chosen is not None
    assert chosen.name == "mock_vendor"


@pytest.mark.parametrize(
    ("state", "source"),
    [
        ("CT", "connecticut_sos_opendata"),
        ("OR", "oregon_sos_opendata"),
        ("OH", "ohio_sos_bulk"),
    ],
)
def test_other_real_state_connectors_win(state: str, source: str) -> None:
    registry = build_default_registry(_factory())
    chosen = registry.select(state=state, capability=CAP_STATUS)
    assert chosen is not None
    assert chosen.name == source


def test_without_session_factory_only_mock_registered() -> None:
    registry = build_default_registry()
    chosen = registry.select(state="CO", capability=CAP_STATUS)
    assert chosen is not None
    assert chosen.name == "mock_vendor"  # no Colorado connector without a DB
