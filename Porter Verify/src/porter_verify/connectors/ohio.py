"""Parser for Ohio Secretary of State business bulk exports.

Ohio has changed bulk-file headings over time. This parser accepts the known
heading variants, preserves the complete row, and never infers unavailable data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _row_value(row: dict, *aliases: str) -> str | None:
    values = {_key(str(k)): v for k, v in row.items()}
    for alias in aliases:
        value = values.get(_key(alias))
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None


def _join(*parts: str | None) -> str | None:
    return " ".join(part.strip() for part in parts if part and part.strip()) or None


@dataclass(frozen=True)
class OhBusinessRecord:
    entity_id: str
    legal_name: str
    status_raw: str | None
    entity_type: str | None
    formation_date: date | None
    principal_address: str | None
    mailing_address: str | None
    jurisdiction: str | None
    source_record_url: str | None
    agent_name: str | None
    agent_address: str | None
    officers: list[dict]
    raw: dict


def parse_oh_record(row: dict) -> OhBusinessRecord:
    """Normalize one Ohio bulk-export row without discarding source columns."""

    principal = _row_value(row, "principal address", "business address", "address")
    if not principal:
        principal = _join(
            _row_value(row, "address 1", "address1", "street"),
            _row_value(row, "address 2", "address2"),
            _row_value(row, "city"),
            _row_value(row, "state"),
            _row_value(row, "zip", "zip code", "postal code"),
        )

    return OhBusinessRecord(
        entity_id=_row_value(
            row, "charter number", "charter no", "entity number", "entity id", "document number"
        )
        or "",
        legal_name=_row_value(row, "business name", "entity name", "name") or "",
        status_raw=_row_value(row, "status", "entity status"),
        entity_type=_row_value(row, "entity type", "business type", "type"),
        formation_date=_date(
            _row_value(row, "filing date", "formation date", "effective date", "creation date")
        ),
        principal_address=principal,
        mailing_address=_row_value(row, "mailing address"),
        jurisdiction=_row_value(row, "jurisdiction", "state of formation", "domestic state"),
        source_record_url=_row_value(row, "record url", "detail url", "source url"),
        agent_name=_row_value(row, "statutory agent", "agent name", "registered agent"),
        agent_address=_row_value(row, "agent address", "statutory agent address"),
        officers=[],
        raw=dict(row),
    )
