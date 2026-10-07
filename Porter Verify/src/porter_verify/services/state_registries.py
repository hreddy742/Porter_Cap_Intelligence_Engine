"""State registry table lookup helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from porter_verify.db.models import (
    AlBusinessEntity,
    CoBusinessEntity,
    CtBusinessEntity,
    FlBusinessEntity,
    GaBusinessEntity,
    MsBusinessEntity,
    OhBusinessEntity,
    OrBusinessEntity,
    TnBusinessEntity,
    TxBusinessEntity,
    VaBusinessEntity,
)
from porter_verify.services.entity_resolution import name_sim
from porter_verify.services.normalization import normalize_name

STATE_MODELS = {
    "AL": AlBusinessEntity,
    "CO": CoBusinessEntity,
    "CT": CtBusinessEntity,
    "FL": FlBusinessEntity,
    "GA": GaBusinessEntity,
    "MS": MsBusinessEntity,
    "OH": OhBusinessEntity,
    "OR": OrBusinessEntity,
    "TN": TnBusinessEntity,
    "TX": TxBusinessEntity,
    "VA": VaBusinessEntity,
}


@dataclass(frozen=True)
class RegistryCounts:
    record_counts: dict[str, int]
    last_refresh_timestamps: dict[str, datetime | None]


def supported_states() -> list[str]:
    return sorted(STATE_MODELS)


def find_registry_match(session: Session, company: str, state: str):
    model = STATE_MODELS.get(state.upper())
    if model is None:
        return None

    normalized = normalize_name(company)
    candidates = session.scalars(
        select(model).where(model.normalized_name == normalized).limit(25)
    ).all()
    if candidates:
        return max(candidates, key=lambda row: name_sim(company, row.entity_name))

    candidates = session.scalars(
        select(model)
        .where(
            or_(
                model.normalized_name.like(f"%{normalized}%"),
                model.entity_name.like(f"%{company}%"),
            )
        )
        .limit(25)
    ).all()
    if not candidates:
        return None
    return max(candidates, key=lambda row: name_sim(company, row.entity_name))


def registry_confidence(company: str, entity_name: str) -> float:
    return round(name_sim(company, entity_name), 4)


def registry_counts(session: Session) -> RegistryCounts:
    counts: dict[str, int] = {}
    refreshes: dict[str, datetime | None] = {}
    for state, model in STATE_MODELS.items():
        counts[state] = session.scalar(select(func.count()).select_from(model)) or 0
        refreshes[state] = session.scalar(select(func.max(model.updated_at)))
    return RegistryCounts(record_counts=counts, last_refresh_timestamps=refreshes)
