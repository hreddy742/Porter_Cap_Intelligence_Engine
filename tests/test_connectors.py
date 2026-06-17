"""Connector contract + behavior tests.

The contract tests run EVERY connector through the same checks — this is what
proves swappability (plan §5.4: "a second stub passes the same contract tests").
"""

from __future__ import annotations

import pytest

from porter_verify.connectors.base import (
    CAP_ENTITY,
    CAP_STATUS,
    ConnectorQuery,
    ConnectorRegistry,
    RawRecord,
    RawResult,
    SourceConnector,
    SourceHealth,
    SourceRef,
    SourceUnavailableError,
)
from porter_verify.connectors.mock_vendor import MockVendorConnector


class StubConnector:
    """A second, minimal connector — exists only to prove the contract is generic."""

    name = "stub"
    capabilities = {CAP_ENTITY, CAP_STATUS}
    states = {"NY"}

    def search(self, query: ConnectorQuery) -> list[RawResult]:
        ref = SourceRef(source_name=self.name, state="NY", reg_id="NY-1")
        return [
            RawResult(
                ref=ref,
                legal_name="Stub Co",
                state="NY",
                reg_id="NY-1",
                status_raw="Active",
                raw={"legal_name": "Stub Co"},
            )
        ]

    def fetch(self, ref: SourceRef) -> RawRecord:
        return RawRecord(ref=ref, raw={"legal_name": "Stub Co"})

    def health(self) -> SourceHealth:
        return SourceHealth(status="healthy")


# Every connector instance the platform ships must pass the contract tests.
ALL_CONNECTORS = [MockVendorConnector(), StubConnector()]


@pytest.mark.parametrize("connector", ALL_CONNECTORS, ids=lambda c: c.name)
def test_connector_satisfies_protocol(connector: SourceConnector) -> None:
    assert isinstance(connector, SourceConnector)
    assert isinstance(connector.name, str) and connector.name
    assert isinstance(connector.capabilities, set)
    assert isinstance(connector.states, set)


@pytest.mark.parametrize("connector", ALL_CONNECTORS, ids=lambda c: c.name)
def test_search_returns_raw_results(connector: SourceConnector) -> None:
    results = connector.search(ConnectorQuery(name="Stub Co", state=None))
    assert isinstance(results, list)
    assert all(isinstance(r, RawResult) for r in results)


@pytest.mark.parametrize("connector", ALL_CONNECTORS, ids=lambda c: c.name)
def test_health_returns_source_health(connector: SourceConnector) -> None:
    assert isinstance(connector.health(), SourceHealth)


# --- Mock vendor behavior -------------------------------------------------


def test_mock_search_finds_company_by_name() -> None:
    results = MockVendorConnector().search(ConnectorQuery(name="Acme Logistics"))
    assert any(r.legal_name == "Acme Logistics LLC" for r in results)


def test_mock_search_respects_state_filter() -> None:
    results = MockVendorConnector().search(ConnectorQuery(name="Acme Logistics", state="CA"))
    assert results == []


def test_mock_fetch_returns_full_record() -> None:
    vendor = MockVendorConnector()
    ref = SourceRef(source_name="mock_vendor", state="TX", reg_id="TX-0801234")
    record = vendor.fetch(ref)
    assert record.response_code == 200
    assert record.raw["officers"][0]["title"] == "Managing Member"


def test_unavailable_connector_raises() -> None:
    vendor = MockVendorConnector(available=False)
    assert vendor.health().status == "unavailable"
    with pytest.raises(SourceUnavailableError):
        vendor.search(ConnectorQuery(name="Acme Logistics"))


# --- Registry selection ---------------------------------------------------


def test_registry_selects_by_capability_and_state() -> None:
    registry = ConnectorRegistry()
    registry.register(MockVendorConnector())
    registry.register(StubConnector())

    # NY-only stub should not be picked for TX; the nationwide mock should.
    chosen = registry.select(state="TX", capability=CAP_STATUS)
    assert chosen is not None
    assert chosen.name == "mock_vendor"


def test_registry_returns_none_when_no_capability() -> None:
    registry = ConnectorRegistry()
    registry.register(StubConnector())
    assert registry.select(state="NY", capability="ucc") is None


def test_registry_skips_unavailable_connectors() -> None:
    registry = ConnectorRegistry()
    registry.register(MockVendorConnector(available=False))
    assert registry.select(state="TX", capability=CAP_ENTITY) is None
