"""Builders for the connector registry.

The default registry wires up the connectors available in the current environment.
When a database session factory is provided, the Colorado open-data connector is
registered (it reads our ingested copy of the state dataset). The built-in mock
vendor remains as a nationwide fallback for states with no real connector yet.

Selection picks the first matching connector, so the Colorado connector is
registered FIRST — for ``state=CO`` it wins; for other states it is skipped
(states={"CO"}) and the nationwide mock handles them.
"""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.connectors.colorado_connector import ColoradoOpenDataConnector
from porter_verify.connectors.connecticut_connector import ConnecticutOpenDataConnector
from porter_verify.connectors.mock_vendor import MockVendorConnector
from porter_verify.connectors.ohio_connector import OhioOpenDataConnector
from porter_verify.connectors.oregon_connector import OregonOpenDataConnector


def build_default_registry(session_factory: sessionmaker | None = None) -> ConnectorRegistry:
    registry = ConnectorRegistry()
    # State-specific real connectors first (they win for their state).
    if session_factory is not None:
        registry.register(ColoradoOpenDataConnector(session_factory))
        registry.register(ConnecticutOpenDataConnector(session_factory))
        registry.register(OregonOpenDataConnector(session_factory))
        registry.register(OhioOpenDataConnector(session_factory))
    # Nationwide fallback last.
    registry.register(MockVendorConnector())
    return registry
