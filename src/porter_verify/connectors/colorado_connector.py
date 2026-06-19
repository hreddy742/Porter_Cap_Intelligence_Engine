"""Colorado open-data connector — a real data source, no API, no scraping.

Implements the standard ``SourceConnector`` contract over the ``co_business_entities``
staging table (populated by the bulk ingest). The verify flow treats it exactly like
any other source: it searches, fetches, and produces a company with evidence + audit.

Because it queries the database, the connector is constructed with a session factory
(the live connectors are stateless; this one reads our ingested copy). It builds the
same raw payload shape the verify flow already understands, so nothing downstream
changes.
"""

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
from porter_verify.db.models import CoBusinessEntity
from porter_verify.services.normalization import normalize_name

# The public Colorado open-data dataset this connector is built from.
CO_DATASET_URL = "https://data.colorado.gov/Business/Business-Entities-in-Colorado/4ykn-tg5h"


def _to_raw(row: CoBusinessEntity) -> dict:
    """Build the raw payload shape the verify flow consumes (same as other sources)."""

    return {
        "legal_name": row.entity_name,
        "state": "CO",
        "reg_id": row.entity_id,
        "entity_type": row.entity_type,
        "formation_date": row.formation_date.isoformat() if row.formation_date else None,
        "status_raw": row.status_raw,
        "registered_agent": {"name": row.agent_name, "address": row.agent_address},
        "officers": [],  # Colorado's dataset lists the agent, not officers.
        "address": row.principal_address,
        "mailing_address": row.mailing_address,
        "jurisdiction": row.jurisdiction,
        "source_url": row.source_record_url or CO_DATASET_URL,
        "coverage": {"source": "official_open_data", "officers_published": False},
        "source_record": row.raw,
    }


class ColoradoOpenDataConnector:
    """SourceConnector backed by the ingested Colorado open-data dataset."""

    name = "colorado_sos_opendata"
    capabilities = {CAP_ENTITY, CAP_STATUS}
    states = {"CO"}

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def search(self, query: ConnectorQuery, *, limit: int = 25) -> list[RawResult]:
        # This source only covers Colorado; a non-CO query yields nothing.
        if query.state and query.state.upper() != "CO":
            return []

        needle = normalize_name(query.name)
        if not needle:
            # An empty needle would LIKE-match every row; a blank query finds nothing.
            return []
        with self._session_factory() as session:
            rows = session.scalars(
                select(CoBusinessEntity)
                .where(CoBusinessEntity.normalized_name.contains(needle))
                .order_by(CoBusinessEntity.entity_name)
                .limit(limit)
            ).all()
            return [
                RawResult(
                    ref=SourceRef(source_name=self.name, state="CO", reg_id=row.entity_id),
                    legal_name=row.entity_name,
                    state="CO",
                    reg_id=row.entity_id,
                    status_raw=row.status_raw,
                    raw=_to_raw(row),
                )
                for row in rows
            ]

    def fetch(self, ref: SourceRef) -> RawRecord:
        with self._session_factory() as session:
            row = session.get(CoBusinessEntity, ref.reg_id)
            if row is None:
                return RawRecord(ref=ref, raw={}, response_code=404)
            return RawRecord(ref=ref, raw=_to_raw(row), response_code=200)

    def health(self) -> SourceHealth:
        with self._session_factory() as session:
            count = session.scalar(select(func.count()).select_from(CoBusinessEntity)) or 0
        if count == 0:
            return SourceHealth(status="degraded", detail="No Colorado data ingested yet")
        return SourceHealth(status="healthy", detail=f"{count} CO entities ingested")
