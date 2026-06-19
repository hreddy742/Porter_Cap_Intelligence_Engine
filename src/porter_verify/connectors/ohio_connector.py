"""Ohio connector backed by an ingested official Secretary of State export."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from porter_verify.connectors.base import (
    CAP_ENTITY,
    CAP_STATUS,
    ConnectorQuery,
    RawRecord,
    RawResult,
    SourceHealth,
    SourceRef,
)
from porter_verify.db.models import OhBusinessEntity
from porter_verify.services.normalization import normalize_name

OH_SOURCE_URL = "https://businesssearch.ohiosos.gov/"


def _to_raw(row: OhBusinessEntity) -> dict:
    return {
        "legal_name": row.entity_name,
        "state": "OH",
        "reg_id": row.entity_id,
        "entity_type": row.entity_type,
        "formation_date": row.formation_date.isoformat() if row.formation_date else None,
        "status_raw": row.status_raw,
        "registered_agent": {"name": row.agent_name, "address": row.agent_address},
        "officers": row.officers,
        "address": row.principal_address,
        "mailing_address": row.mailing_address,
        "jurisdiction": row.jurisdiction,
        "source_url": row.source_record_url or OH_SOURCE_URL,
        "coverage": {"source": "official_bulk_file", "officers_published": False},
        "source_record": row.raw,
    }


class OhioOpenDataConnector:
    name = "ohio_sos_bulk"
    capabilities = {CAP_ENTITY, CAP_STATUS}
    states = {"OH"}

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def search(self, query: ConnectorQuery, *, limit: int = 25) -> list[RawResult]:
        if query.state and query.state.upper() != "OH":
            return []
        needle = normalize_name(query.name)
        if not needle:
            return []
        with self._session_factory() as session:
            rows = session.scalars(
                select(OhBusinessEntity)
                .where(OhBusinessEntity.normalized_name.contains(needle))
                .order_by(OhBusinessEntity.entity_name)
                .limit(limit)
            ).all()
            return [
                RawResult(
                    ref=SourceRef(source_name=self.name, state="OH", reg_id=row.entity_id),
                    legal_name=row.entity_name,
                    state="OH",
                    reg_id=row.entity_id,
                    status_raw=row.status_raw,
                    raw=_to_raw(row),
                )
                for row in rows
            ]

    def fetch(self, ref: SourceRef) -> RawRecord:
        with self._session_factory() as session:
            row = session.get(OhBusinessEntity, ref.reg_id)
            if row is None:
                return RawRecord(ref=ref, raw={}, response_code=404)
            return RawRecord(ref=ref, raw=_to_raw(row))

    def health(self) -> SourceHealth:
        with self._session_factory() as session:
            count = session.scalar(select(func.count()).select_from(OhBusinessEntity)) or 0
        if not count:
            return SourceHealth(status="degraded", detail="No Ohio data ingested yet")
        return SourceHealth(status="healthy", detail=f"{count} OH entities ingested")
