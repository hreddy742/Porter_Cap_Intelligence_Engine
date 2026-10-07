"""Connecticut Secretary of State open-data parser.

Connecticut publishes its full business-entity registry on data.ct.gov via the
Socrata SODA API (dataset n7gp-d28j). One row per entity; the key columns we use:

    accountnumber       entity_id (primary key)
    name                legal name
    status              registration status (Active, Rejected, Withdrawn, etc.)
    business_type       entity type (LLC, Corporation, etc.)
    date_registration   formation date (ISO: YYYY-MM-DDT00:00:00.000)

The parser follows the current dataset schema and preserves every source column
in ``raw``. Agent data is not published in this dataset.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CtBusinessRecord:
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
    raw: dict


def _parse_ct_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value.strip()[:10])
        return None if parsed.year <= 1 else parsed
    except ValueError:
        return None


def _join(*parts: str | None) -> str | None:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    return " ".join(cleaned) or None


def _address_value(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, dict):
        return None
    human = value.get("human_address")
    if isinstance(human, str):
        try:
            human = json.loads(human)
        except json.JSONDecodeError:
            return human.strip() or None
    if isinstance(human, dict):
        return _join(
            human.get("address"),
            human.get("city"),
            human.get("state"),
            human.get("zip"),
        )
    return None


def parse_ct_record(row: dict) -> CtBusinessRecord:
    """Map one raw SODA row to a CtBusinessRecord."""
    mailing_address = _address_value(row.get("mailing_address"))
    principal_address = _join(
        row.get("billingstreet"),
        row.get("billing_unit"),
        row.get("billingcity"),
        row.get("billingstate"),
        row.get("billingpostalcode"),
        row.get("billingcountry"),
    )
    return CtBusinessRecord(
        entity_id=(row.get("accountnumber") or "").strip(),
        legal_name=(row.get("name") or "").strip(),
        status_raw=(row.get("status") or "").strip() or None,
        entity_type=(row.get("business_type") or "").strip() or None,
        formation_date=_parse_ct_date(row.get("date_registration")),
        principal_address=principal_address or mailing_address,
        mailing_address=mailing_address,
        jurisdiction=_join(
            row.get("state_or_territory_formation") or row.get("formation_place"),
            row.get("country_formation"),
        ),
        source_record_url=None,
        officers=[],
        raw=dict(row),
    )
