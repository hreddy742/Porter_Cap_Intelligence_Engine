"""Florida Sunbiz business-entity parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class FlBusinessRecord:
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


def parse_fl_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y%m%d", "%m%d%Y"):
        try:
            parsed = datetime.strptime(text[:10], fmt).date()
            if parsed >= date(1800, 1, 1) and parsed <= date.today():
                return parsed
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


def _join(*parts: str | None) -> str | None:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return " ".join(cleaned) or None


def _field(line: str, start: int, end: int) -> str | None:
    value = line[start - 1 : end].strip()
    return value or None


def _source_url(entity_id: str) -> str | None:
    if not entity_id:
        return None
    return f"https://search.sunbiz.org/Inquiry/CorporationSearch/ByDocumentNumber?documentNumber={entity_id}"


def parse_fl_fixed_width(line: str) -> FlBusinessRecord:
    """Parse one Sunbiz corporate fixed-width row.

    Field offsets follow the published Sunbiz corporate data file definition.
    """

    entity_id = _field(line, 1, 12) or ""
    legal_name = _field(line, 13, 204) or ""
    status = _field(line, 205, 205)
    entity_type = _field(line, 206, 209)
    formation_date = parse_fl_date(_field(line, 473, 480))
    principal_address = _join(
        _field(line, 221, 262),
        _field(line, 305, 332),
        _field(line, 335, 344),
    )
    mailing_address = _join(
        _field(line, 347, 388),
        _field(line, 431, 458),
        _field(line, 471, 472),
        _field(line, 461, 470),
    )
    agent_name = _field(line, 545, 586)
    agent_address = _join(
        _field(line, 588, 629),
        _field(line, 630, 657),
        _field(line, 658, 659),
        _field(line, 660, 668),
    )

    return FlBusinessRecord(
        entity_id=entity_id,
        legal_name=legal_name,
        status_raw=status,
        entity_type=entity_type,
        formation_date=formation_date,
        principal_address=principal_address,
        mailing_address=mailing_address,
        jurisdiction="FL",
        source_record_url=_source_url(entity_id),
        officers=[],
        agent_name=agent_name,
        agent_address=agent_address,
        raw={"fixed_width": line.rstrip("\r\n")},
    )


def parse_fl_record(row: dict) -> FlBusinessRecord:
    entity_id = _first(row, "document number", "document_number", "entity id", "entity_id") or ""
    legal_name = _first(row, "corporate name", "entity name", "entity_name", "name") or ""

    return FlBusinessRecord(
        entity_id=entity_id,
        legal_name=legal_name,
        status_raw=_first(row, "status", "entity status"),
        entity_type=_first(row, "filing type", "entity type", "type"),
        formation_date=parse_fl_date(_first(row, "file date", "formation date", "date filed")),
        principal_address=_first(row, "principal address", "address"),
        mailing_address=_first(row, "mailing address"),
        jurisdiction=_first(row, "jurisdiction", "state of formation") or "FL",
        source_record_url=_first(row, "source record url", "source_url") or _source_url(entity_id),
        officers=[],
        agent_name=_first(row, "registered agent", "agent name"),
        agent_address=_first(row, "registered agent address", "agent address"),
        raw=dict(row),
    )
