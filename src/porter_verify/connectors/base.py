"""The SourceConnector contract and its data types (plan §9.3).

Every data source — the purchased SOS/KYB vendor, the built-in mock, a future
direct gov connector — implements this same Protocol. That swappability is the
whole point: the platform is Porter's; the data layer is rented and replaceable.

Connectors return RAW data. They never normalize, score, or persist — those are
the service layer's job. The raw response is preserved verbatim before any parsing
(plan §9.4), which is why ``RawResult``/``RawRecord`` carry a ``raw`` dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Capability strings a connector may advertise.
CAP_ENTITY = "entity"
CAP_STATUS = "status"
CAP_OFFICERS = "officers"
CAP_SCREENSHOT = "screenshot"


@dataclass(frozen=True)
class ConnectorQuery:
    """A search request to a connector."""

    name: str
    state: str | None = None


@dataclass(frozen=True)
class SourceRef:
    """A stable handle to one record at a source (used to fetch full detail)."""

    source_name: str
    state: str
    reg_id: str


@dataclass(frozen=True)
class RawResult:
    """A single search hit. ``raw`` holds the verbatim source payload."""

    ref: SourceRef
    legal_name: str
    state: str
    reg_id: str
    status_raw: str | None
    raw: dict


@dataclass(frozen=True)
class RawRecord:
    """A fully fetched record. ``raw`` is preserved verbatim for reprocessing."""

    ref: SourceRef
    raw: dict
    response_code: int = 200
    latency_ms: int = 0


@dataclass(frozen=True)
class SourceHealth:
    """A connector's self-reported health."""

    status: str = "healthy"  # healthy | degraded | unavailable
    detail: str = ""


class SourceUnavailableError(RuntimeError):
    """Raised when a source cannot be reached. The flow records it without charge."""


@runtime_checkable
class SourceConnector(Protocol):
    """The contract every connector must satisfy (see ``tests/test_connectors``)."""

    name: str
    capabilities: set[str]
    states: set[str]

    def search(self, query: ConnectorQuery) -> list[RawResult]:
        """Return candidate records matching the query (may be empty)."""
        ...

    def fetch(self, ref: SourceRef) -> RawRecord:
        """Fetch the full verbatim record for a reference."""
        ...

    def health(self) -> SourceHealth:
        """Report current health (used for selection and the health dashboard)."""
        ...


@dataclass
class ConnectorRegistry:
    """Holds connectors and selects one by capability + state coverage + health.

    ``states`` empty on a connector means nationwide / non-state coverage.
    """

    _connectors: dict[str, SourceConnector] = field(default_factory=dict)

    def register(self, connector: SourceConnector) -> None:
        self._connectors[connector.name] = connector

    def get(self, name: str) -> SourceConnector | None:
        return self._connectors.get(name)

    def all(self) -> list[SourceConnector]:
        return list(self._connectors.values())

    def select(self, *, state: str | None, capability: str) -> SourceConnector | None:
        """Pick the first healthy connector with the capability covering the state."""

        for connector in self._connectors.values():
            if capability not in connector.capabilities:
                continue
            covers_state = (
                state is None or not connector.states or state.upper() in connector.states
            )
            if not covers_state:
                continue
            # A connector whose health check errors is treated as unavailable and
            # skipped — one bad connector must never crash source selection.
            try:
                if connector.health().status == "unavailable":
                    continue
            except Exception:
                continue
            return connector
        return None
