"""Virginia SCC business-entity parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class VaBusinessRecord:
    entity_id: str
    legal_name: str
    status_raw: str | None
    entity_type: str | None
    formation_date: date | None
    principal_address: str | None
    mailing_address: str | None
    jurisdiction: str | None
    source_record_url: str | None
    officers: list[dict]
    agent_name: str | None
    agent_address: str | None
    raw: dict


def parse_va_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _first(row: dict, *names: str) -> str | None:
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _source_url(entity_id: str) -> str | None:
    if not entity_id:
        return None
    return f"https://cis.scc.virginia.gov/EntitySearch/BusinessInformation?businessId={entity_id}"


def parse_va_record(row: dict) -> VaBusinessRecord:
    entity_id = _first(row, "entity id", "entity_id", "scc id", "id") or ""
    legal_name = _first(row, "entity name", "business name", "legal name", "name") or ""

    return VaBusinessRecord(
        entity_id=entity_id,
        legal_name=legal_name,
        status_raw=_first(row, "status", "entity status"),
        entity_type=_first(row, "entity type", "business type", "type"),
        formation_date=parse_va_date(
            _first(row, "formation date", "date formed", "effective date")
        ),
        principal_address=_first(row, "principal office address", "principal address", "address"),
        mailing_address=_first(row, "mailing address"),
        jurisdiction=_first(row, "jurisdiction", "state of formation", "formation state"),
        source_record_url=_first(row, "source record url", "source_url") or _source_url(entity_id),
        officers=[],
        agent_name=_first(row, "registered agent", "registered agent name", "agent name"),
        agent_address=_first(row, "registered agent address", "agent address"),
        raw=dict(row),
    )
