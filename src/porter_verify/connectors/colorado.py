"""Colorado Secretary-of-State open-data connector.

Colorado publishes its **entire** business-entity dataset for free download
(data.colorado.gov, 1M+ records). That means we acquire real CO data with **no
data API and no scraping** — just download the file and ingest it. This module
holds the small, pure parsing functions that turn one raw CSV row into the fields
our pipeline needs. The DB ingest and the connector class build on these.

Karpathy principle in force here: keep it boring and inspectable — plain functions,
explicit field names, no magic. You can read a row and predict the output.

Real column names (confirmed from the live dataset):
    entityid, entityname, principaladdress1/2, principalcity/state/zipcode,
    entitystatus, entitytype, entityformdate (ISO w/ time),
    agentfirstname/middlename/lastname/suffix, agentorganizationname,
    agentprincipaladdress1/2, agentprincipalcity/state/zipcode
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CoBusinessRecord:
    """Canonical view of one Colorado business-entity row."""

    entity_id: str
    legal_name: str
    status_raw: str | None
    entity_type: str | None
    formation_date: date | None
    principal_address: str | None
    agent_name: str | None
    agent_address: str | None
    raw: dict


def parse_co_date(value: str | None) -> date | None:
    """Parse Colorado's ``2025-06-16T00:00:00.000`` timestamp into a date.

    Returns None for blank/unparseable values (never guesses).
    """

    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])  # take the YYYY-MM-DD prefix
    except ValueError:
        return None


def _join(*parts: str | None) -> str | None:
    """Join non-empty, stripped parts with a single space; None if all empty."""

    cleaned = [p.strip() for p in parts if p and p.strip()]
    return " ".join(cleaned) or None


def _agent_name(row: dict) -> str | None:
    """Agent name: the organization name if present, else the person's full name."""

    org = (row.get("agentorganizationname") or "").strip()
    if org:
        return org
    return _join(
        row.get("agentfirstname"),
        row.get("agentmiddlename"),
        row.get("agentlastname"),
        row.get("agentsuffix"),
    )


def _address(row: dict, prefix: str) -> str | None:
    """Build a single-line address from the ``prefix`` address columns."""

    return _join(
        row.get(f"{prefix}address1"),
        row.get(f"{prefix}address2"),
        row.get(f"{prefix}city"),
        row.get(f"{prefix}state"),
        row.get(f"{prefix}zipcode"),
    )


def parse_record(row: dict) -> CoBusinessRecord:
    """Map one raw CSV row (as a dict) to a ``CoBusinessRecord``.

    The full raw row is preserved on ``.raw`` so nothing is lost before
    normalization (same raw-before-normalized rule as every other source).
    """

    return CoBusinessRecord(
        entity_id=(row.get("entityid") or "").strip(),
        legal_name=(row.get("entityname") or "").strip(),
        status_raw=(row.get("entitystatus") or "").strip() or None,
        entity_type=(row.get("entitytype") or "").strip() or None,
        formation_date=parse_co_date(row.get("entityformdate")),
        principal_address=_address(row, "principal"),
        agent_name=_agent_name(row),
        agent_address=_address(row, "agentprincipal"),
        raw=dict(row),
    )
