"""Mississippi Secretary of State business-entity parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class MsBusinessRecord:
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


def parse_ms_date(value: str | None) -> date | None:
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
    return f"https://corp.sos.ms.gov/corp/portal/c/page/corpBusinessIdSearch/portal.aspx?businessId={entity_id}"


def parse_ms_record(row: dict) -> MsBusinessRecord:
    entity_id = _first(row, "business id", "business_id", "entity id", "entity_id", "id") or ""
    legal_name = _first(row, "business name", "entity name", "entity_name", "name") or ""

    return MsBusinessRecord(
        entity_id=entity_id,
        legal_name=legal_name,
        status_raw=_first(row, "status", "business status", "entity status"),
        entity_type=_first(row, "business type", "entity type", "type"),
        formation_date=parse_ms_date(_first(row, "formation date", "date formed", "created date")),
        principal_address=_first(row, "principal office address", "principal address", "address"),
        mailing_address=_first(row, "mailing address"),
        jurisdiction=_first(row, "jurisdiction", "state of formation", "formation state"),
        source_record_url=_first(row, "source record url", "source_url") or _source_url(entity_id),
        officers=[],
        agent_name=_first(row, "registered agent", "registered agent name", "agent name"),
        agent_address=_first(row, "registered agent address", "agent address"),
        raw=dict(row),
    )
