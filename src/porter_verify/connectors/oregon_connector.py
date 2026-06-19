"""Oregon open-data connector backed by the ingested SODA dataset.

Implements the standard ``SourceConnector`` contract over ``or_business_entities``.
Oregon's dataset contains only active entities, so this connector will only
produce VERIFIED results (no dissolved/delinquent status to surface).
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from porter_verify.connectors.base import (
    CAP_ENTITY,
    CAP_OFFICERS,
    CAP_STATUS,
    ConnectorQuery,
    RawRecord,
    RawResult,
    SourceHealth,
    SourceRef,
)
from porter_verify.db.models import OrBusinessEntity
from porter_verify.services.normalization import normalize_name

OR_DATASET_URL = "https://data.oregon.gov/d/tckn-sxa6"


def _to_raw(row: OrBusinessEntity) -> dict:
    return {
        "legal_name": row.entity_name,
        "state": "OR",
        "reg_id": row.entity_id,
        "entity_type": row.entity_type,
        "formation_date": row.formation_date.isoformat() if row.formation_date else None,
        "status_raw": row.status_raw,
        "registered_agent": {"name": row.agent_name, "address": row.agent_address},
        "officers": row.officers,
        "address": row.principal_address,
        "mailing_address": row.mailing_address,
        "jurisdiction": row.jurisdiction,
        "source_url": row.source_record_url or OR_DATASET_URL,
        "coverage": {"source": "official_open_data", "active_entities_only": True},
        "source_record": row.raw,
    }


class OregonOpenDataConnector:
    """SourceConnector backed by the ingested Oregon SODA dataset."""

    name = "oregon_sos_opendata"
    capabilities = {CAP_ENTITY, CAP_STATUS, CAP_OFFICERS}
    states = {"OR"}

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def search(self, query: ConnectorQuery, *, limit: int = 25) -> list[RawResult]:
        if query.state and query.state.upper() != "OR":
            return []

        needle = normalize_name(query.name)
        if not needle:
            return []

        with self._session_factory() as session:
            rows = session.scalars(
                select(OrBusinessEntity)
                .where(OrBusinessEntity.normalized_name.contains(needle))
                .order_by(OrBusinessEntity.entity_name)
                .limit(limit)
            ).all()
            return [
                RawResult(
                    ref=SourceRef(source_name=self.name, state="OR", reg_id=row.entity_id),
                    legal_name=row.entity_name,
                    state="OR",
                    reg_id=row.entity_id,
                    status_raw=row.status_raw,
                    raw=_to_raw(row),
                )
                for row in rows
            ]

    def fetch(self, ref: SourceRef) -> RawRecord:
        with self._session_factory() as session:
            row = session.get(OrBusinessEntity, ref.reg_id)
            if row is None:
                return RawRecord(ref=ref, raw={}, response_code=404)
            return RawRecord(ref=ref, raw=_to_raw(row), response_code=200)

    def health(self) -> SourceHealth:
        with self._session_factory() as session:
            count = session.scalar(select(func.count()).select_from(OrBusinessEntity)) or 0
        if count == 0:
            return SourceHealth(status="degraded", detail="No Oregon data ingested yet")
        return SourceHealth(status="healthy", detail=f"{count} OR entities ingested")
