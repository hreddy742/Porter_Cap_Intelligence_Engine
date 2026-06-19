"""State-specific filtering for recently formed business leads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func, not_, or_, select
from sqlalchemy.orm import Session

from porter_verify.db.models import (
    CoBusinessEntity,
    CtBusinessEntity,
    OhBusinessEntity,
    OrBusinessEntity,
)

MODELS: dict[str, type] = {
    "CO": CoBusinessEntity,
    "CT": CtBusinessEntity,
    "OR": OrBusinessEntity,
    "OH": OhBusinessEntity,
}

ACTIVE_STATUSES = {
    "CO": {"GOOD STANDING"},
    "CT": {"ACTIVE"},
    "OR": {"ACTIVE"},
    "OH": {"ACTIVE", "GOOD STANDING"},
}


@dataclass(frozen=True)
class RecentBusinessRecord:
    state: str
    entity: Any
    domestic_signal: bool
    active_signal: bool
    nonprofit_signal: bool
    relevant_entity_signal: bool
    jurisdiction: str | None
    source_record_url: str
    date_basis: str


def _upper(column):  # noqa: ANN001, ANN202
    return func.upper(func.coalesce(column, ""))


def _active_condition(state: str, model: type):
    return _upper(model.status_raw).in_(ACTIVE_STATUSES[state])


def _domestic_condition(state: str, model: type):
    entity_type = _upper(model.entity_type)
    jurisdiction = _upper(model.jurisdiction)
    if state == "CO":
        return entity_type.like("D%") & (jurisdiction == "CO")
    if state == "CT":
        citizenship = _upper(model.raw["citizenship"].as_string())
        return or_(
            citizenship == "DOMESTIC",
            jurisdiction == "CT",
            jurisdiction.like("%CONNECTICUT%"),
        )
    if state == "OR":
        return entity_type.like("DOMESTIC%") & (jurisdiction == "OR")
    return or_(
        entity_type.like("DOMESTIC%"),
        jurisdiction == "OH",
        jurisdiction.like("%OHIO%"),
    )


def _nonprofit_condition(state: str, model: type):
    entity_type = _upper(model.entity_type)
    conditions = [entity_type.like("%NONPROFIT%"), entity_type.like("%NON-STOCK%")]
    if state == "CO":
        conditions.extend((entity_type == "DNC", entity_type == "FNC"))
    return or_(*conditions)


def _relevant_condition(state: str, model: type):
    entity_type = _upper(model.entity_type)
    irrelevant = or_(
        entity_type == "",
        entity_type.like("%ASSUMED BUSINESS NAME%"),
        entity_type.like("%TRADE NAME%"),
        entity_type.like("%RESERV%"),
        _nonprofit_condition(state, model),
    )
    return not_(irrelevant)


def _is_active(state: str, entity: Any) -> bool:
    return (entity.status_raw or "").strip().upper() in ACTIVE_STATUSES[state]


def _is_domestic(state: str, entity: Any) -> bool:
    entity_type = (entity.entity_type or "").strip().upper()
    jurisdiction = (entity.jurisdiction or "").strip().upper()
    if state == "CO":
        return entity_type.startswith("D") and jurisdiction == "CO"
    if state == "CT":
        citizenship = str((entity.raw or {}).get("citizenship") or "").strip().upper()
        return (
            citizenship == "DOMESTIC"
            or jurisdiction == "CT"
            or "CONNECTICUT" in jurisdiction
        )
    if state == "OR":
        return entity_type.startswith("DOMESTIC") and jurisdiction == "OR"
    return entity_type.startswith("DOMESTIC") or jurisdiction == "OH" or "OHIO" in jurisdiction


def _is_nonprofit(state: str, entity: Any) -> bool:
    entity_type = (entity.entity_type or "").strip().upper()
    return (
        "NONPROFIT" in entity_type
        or "NON-STOCK" in entity_type
        or (state == "CO" and entity_type in {"DNC", "FNC"})
    )


def _is_relevant(state: str, entity: Any) -> bool:
    entity_type = (entity.entity_type or "").strip().upper()
    return bool(entity_type) and not any(
        term in entity_type for term in ("ASSUMED BUSINESS NAME", "TRADE NAME", "RESERV")
    ) and not _is_nonprofit(state, entity)


def _jurisdiction(state: str, entity: Any) -> str | None:
    if entity.jurisdiction or state != "CT":
        return entity.jurisdiction
    raw = entity.raw or {}
    formation_state = raw.get("state_or_territory_formation") or raw.get("formation_place")
    country = raw.get("country_formation")
    return " ".join(str(value).strip() for value in (formation_state, country) if value) or None


def _source_url(state: str, entity: Any) -> str:
    if state == "OR":
        return (
            "https://data.oregon.gov/resource/tckn-sxa6.json"
            f"?registry_number={entity.entity_id}"
        )
    if entity.source_record_url:
        return entity.source_record_url
    if state == "CO":
        return f"https://data.colorado.gov/resource/4ykn-tg5h.json?entityid={entity.entity_id}"
    if state == "CT":
        return f"https://data.ct.gov/resource/n7gp-d28j.json?accountnumber={entity.entity_id}"
    return "https://businesssearch.ohiosos.gov/"


def _date_basis(state: str) -> str:
    return {
        "CO": "Entity formation date",
        "CT": "State registration date",
        "OR": "State registry date",
        "OH": "State filing/formation date",
    }[state]


def _record(state: str, entity: Any) -> RecentBusinessRecord:
    return RecentBusinessRecord(
        state=state,
        entity=entity,
        domestic_signal=_is_domestic(state, entity),
        active_signal=_is_active(state, entity),
        nonprofit_signal=_is_nonprofit(state, entity),
        relevant_entity_signal=_is_relevant(state, entity),
        jurisdiction=_jurisdiction(state, entity),
        source_record_url=_source_url(state, entity),
        date_basis=_date_basis(state),
    )


def get_recent_business(
    session: Session, *, state: str, entity_id: str
) -> RecentBusinessRecord | None:
    entity = session.get(MODELS[state], entity_id)
    return _record(state, entity) if entity is not None else None


def find_recent_businesses(
    session: Session,
    *,
    states: list[str],
    formed_from: date,
    formed_to: date,
    limit: int,
) -> list[RecentBusinessRecord]:
    """Return newest qualifying records across selected state staging tables."""

    records: list[RecentBusinessRecord] = []
    for state in states:
        model = MODELS[state]
        conditions = [
            model.formation_date >= formed_from,
            model.formation_date <= formed_to,
        ]
        entities = session.scalars(
            select(model)
            .where(*conditions)
            .order_by(model.formation_date.desc(), model.entity_name, model.entity_id)
            .limit(limit)
        )
        for entity in entities:
            records.append(_record(state, entity))

    records.sort(
        key=lambda item: (
            item.entity.formation_date or date.min,
            item.entity.entity_name,
            item.state,
        ),
        reverse=True,
    )
    return records[:limit]
