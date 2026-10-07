"""Oregon Secretary of State open-data parser.

Oregon's SODA dataset (tckn-sxa6) uses a **long** format: one row per
name/address *type* rather than one row per entity. The key discriminator
column is ``associated_name_type``, with values like:

    PRINCIPAL PLACE OF BUSINESS   — entity info + principal address
    REGISTERED AGENT               — agent name + agent address
    MAILING ADDRESS                — mailing address
    AUTHORIZED REPRESENTATIVE      — additional published representative

This module pivots the raw long rows into one ``OrBusinessRecord`` per entity
using the registry_number as the grouping key. The caller (ingest script) is
responsible for grouping rows by registry_number before calling
``pivot_or_rows``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class OrBusinessRecord:
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
    raw: dict  # merged from all rows for this entity


def _parse_or_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _join(*parts: str | None) -> str | None:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    return " ".join(cleaned) or None


def pivot_or_rows(rows: list[dict]) -> OrBusinessRecord | None:
    """Pivot a list of long-format rows (same registry_number) into one record.

    Returns None if no PRINCIPAL PLACE OF BUSINESS row is found (can't determine
    entity name), or if the registry_number is blank.
    """
    principal: dict | None = None
    agent: dict | None = None
    mailing: dict | None = None
    representatives: list[dict] = []

    for row in rows:
        kind = (row.get("associated_name_type") or "").strip().upper()
        if kind == "PRINCIPAL PLACE OF BUSINESS":
            principal = row
        elif kind == "REGISTERED AGENT":
            agent = row
        elif kind == "MAILING ADDRESS":
            mailing = row
        elif kind == "AUTHORIZED REPRESENTATIVE":
            representatives.append(row)

    if principal is None:
        return None

    entity_id = (principal.get("registry_number") or "").strip()
    legal_name = (principal.get("business_name") or "").strip()
    if not entity_id or not legal_name:
        return None

    principal_address = _join(
        principal.get("address"),
        principal.get("address_continued"),
        principal.get("city"),
        principal.get("state"),
        principal.get("zip"),
    )

    agent_name: str | None = None
    agent_address: str | None = None
    if agent is not None:
        agent_name = (agent.get("entity_of_record_name") or "").strip() or _join(
            agent.get("first_name"),
            agent.get("middle_name"),
            agent.get("last_name"),
            agent.get("suffix"),
        )
        agent_address = _join(
            agent.get("address"),
            agent.get("address_continued"),
            agent.get("city"),
            agent.get("state"),
            agent.get("zip"),
        )

    def person_name(row: dict) -> str | None:
        return (row.get("entity_of_record_name") or "").strip() or _join(
            row.get("first_name"), row.get("middle_name"), row.get("last_name"), row.get("suffix")
        )

    officers = [
        {
            "name": name,
            "title": "Authorized Representative",
            "address": _join(
                row.get("address"),
                row.get("address_continued"),
                row.get("city"),
                row.get("state"),
                row.get("zip"),
            ),
        }
        for row in representatives
        if (name := person_name(row))
    ]

    details = principal.get("business_details")
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except json.JSONDecodeError:
            details = {"url": details} if details.startswith("http") else None
    source_record_url = details.get("url") if isinstance(details, dict) else None

    return OrBusinessRecord(
        entity_id=entity_id,
        legal_name=legal_name,
        # OR only publishes active entities — status field is blank in the dataset.
        status_raw=(principal.get("status") or "").strip() or "Active",
        entity_type=(principal.get("entity_type") or "").strip() or None,
        formation_date=_parse_or_date(principal.get("registry_date")),
        principal_address=principal_address,
        mailing_address=_join(
            mailing.get("address") if mailing else None,
            mailing.get("address_continued") if mailing else None,
            mailing.get("city") if mailing else None,
            mailing.get("state") if mailing else None,
            mailing.get("zip") if mailing else None,
        ),
        jurisdiction=(principal.get("jurisdiction") or "").strip() or None,
        source_record_url=source_record_url,
        agent_name=agent_name,
        agent_address=agent_address,
        officers=officers,
        raw={"rows": [dict(row) for row in rows]},
    )
