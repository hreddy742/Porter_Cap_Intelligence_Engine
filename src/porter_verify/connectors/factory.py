"""Builders for the connector registry.

The default registry wires up the connectors available in the current environment.
In the MVP that is the built-in mock vendor; a real SOS/KYB vendor connector is
added here once credentials are configured (the rest of the system is unchanged —
that is the swappability guarantee).
"""

from __future__ import annotations

from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.connectors.mock_vendor import MockVendorConnector


def build_default_registry() -> ConnectorRegistry:
    registry = ConnectorRegistry()
    registry.register(MockVendorConnector())
    return registry
