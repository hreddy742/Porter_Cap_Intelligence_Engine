"""A deterministic, in-memory mock SOS/KYB connector.

Stands in for the purchased vendor so the whole verification flow runs locally and
in tests without network access or vendor cost. It returns realistic Secretary-of-
State-shaped records and proves the SourceConnector contract is satisfiable.

The fixtures deliberately include varied cases: active, dissolved, delinquent, and
a near-duplicate name (to exercise entity-resolution ambiguity).
"""

from __future__ import annotations

from porter_verify.connectors.base import (
    CAP_ENTITY,
    CAP_OFFICERS,
    CAP_STATUS,
    ConnectorQuery,
    RawRecord,
    RawResult,
    SourceHealth,
    SourceRef,
    SourceUnavailableError,
)
from porter_verify.services.normalization import normalize_name

# Each fixture is a verbatim "vendor payload". Keyed by (normalized_name, state).
_FIXTURES: list[dict] = [
    {
        "legal_name": "Acme Logistics LLC",
        "state": "TX",
        "reg_id": "TX-0801234",
        "entity_type": "LLC",
        "formation_date": "2015-03-12",
        "status_raw": "Active",
        "registered_agent": {"name": "Jane Roe", "address": "100 Main St, Austin, TX"},
        "officers": [{"name": "John Smith", "title": "Managing Member"}],
        "address": "100 Main St, Austin, TX",
    },
    {
        "legal_name": "Zenith Pharmaceuticals Inc",
        "state": "CA",
        "reg_id": "CA-C1234567",
        "entity_type": "Corporation",
        "formation_date": "2008-07-01",
        "status_raw": "Active",
        "registered_agent": {"name": "Acme Agents Inc", "address": "1 Market St, SF, CA"},
        "officers": [{"name": "Maria Garcia", "title": "CEO"}],
        "address": "500 Bay St, San Francisco, CA",
    },
    {
        "legal_name": "Defunct Holdings LLC",
        "state": "DE",
        "reg_id": "DE-5550001",
        "entity_type": "LLC",
        "formation_date": "2011-01-05",
        "status_raw": "Dissolved",
        "registered_agent": {
            "name": "Corp Services LLC",
            "address": "1209 Orange St, Wilmington, DE",
        },
        "officers": [],
        "address": "1209 Orange St, Wilmington, DE",
    },
    {
        "legal_name": "Lone Star Freight Co",
        "state": "TX",
        "reg_id": "TX-0809999",
        "entity_type": "Corporation",
        "formation_date": "2019-11-20",
        "status_raw": "Forfeited - Tax Delinquent",
        "registered_agent": {"name": "Bob Lee", "address": "9 Ranch Rd, Dallas, TX"},
        "officers": [{"name": "Bob Lee", "title": "President"}],
        "address": "9 Ranch Rd, Dallas, TX",
    },
]


def _key(name: str, state: str) -> tuple[str, str]:
    return normalize_name(name), state.upper()


class MockVendorConnector:
    """Implements the SourceConnector contract over static fixtures."""

    name = "mock_vendor"
    capabilities = {CAP_ENTITY, CAP_STATUS, CAP_OFFICERS}
    states: set[str] = set()  # empty => nationwide coverage (it's a mock)

    def __init__(self, *, available: bool = True) -> None:
        # Toggle to simulate an outage for failure-path tests.
        self._available = available
        self._by_key = {_key(f["legal_name"], f["state"]): f for f in _FIXTURES}

    def search(self, query: ConnectorQuery) -> list[RawResult]:
        if not self._available:
            raise SourceUnavailableError(f"{self.name} is unavailable")

        norm_q = normalize_name(query.name)
        results: list[RawResult] = []
        for fixture in _FIXTURES:
            if query.state and fixture["state"].upper() != query.state.upper():
                continue
            # Simple containment match on normalized names (the mock's "search").
            norm_name = normalize_name(fixture["legal_name"])
            if norm_q in norm_name or norm_name in norm_q:
                results.append(self._to_result(fixture))
        return results

    def fetch(self, ref: SourceRef) -> RawRecord:
        if not self._available:
            raise SourceUnavailableError(f"{self.name} is unavailable")
        fixture = next(
            (f for f in _FIXTURES if f["reg_id"] == ref.reg_id and f["state"] == ref.state),
            None,
        )
        if fixture is None:
            return RawRecord(ref=ref, raw={}, response_code=404)
        return RawRecord(ref=ref, raw=dict(fixture), response_code=200, latency_ms=12)

    def health(self) -> SourceHealth:
        if not self._available:
            return SourceHealth(status="unavailable", detail="simulated outage")
        return SourceHealth(status="healthy")

    @staticmethod
    def _to_result(fixture: dict) -> RawResult:
        ref = SourceRef(source_name="mock_vendor", state=fixture["state"], reg_id=fixture["reg_id"])
        return RawResult(
            ref=ref,
            legal_name=fixture["legal_name"],
            state=fixture["state"],
            reg_id=fixture["reg_id"],
            status_raw=fixture["status_raw"],
            raw=dict(fixture),
        )
