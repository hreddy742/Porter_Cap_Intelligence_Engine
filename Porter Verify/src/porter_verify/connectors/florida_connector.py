"""Florida open-data connector -- reads the ingested Sunbiz bulk dataset.

Implements the standard ``SourceConnector`` contract over the
``fl_business_entities`` staging table, following the same pattern as
Colorado/Oregon. Florida's fixed-width record layout documents the status
field (byte 205) as only having two defined values -- 'A' (active) and 'I'
(inactive) -- per the official Corporate Data File Definitions
(https://dos.sunbiz.org/data-definitions/cor.html). Other observed raw codes
('D', 'L', 'F', ...) are NOT documented anywhere in that spec, so this
connector does not guess a meaning for them: it maps only the two documented
codes to readable text and passes everything else through verbatim, letting
``normalize_status`` correctly classify the undocumented ones as UNKNOWN
rather than fabricating a status.

Officers are never populated in the ingested dataset (checked: 0 of 11.6M
rows have any), so this connector does not claim CAP_OFFICERS.
"""

from __future__ import annotations

from sqlalchemy import func, select, text
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
from porter_verify.db.models import FlBusinessEntity
from porter_verify.services.normalization import normalize_name

FL_DATASET_URL = "https://dos.fl.gov/sunbiz/other-services/data-downloads/"

# Only these two codes are documented in Florida's official Corporate Data
# File Definitions. Anything else is passed through raw rather than guessed.
_DOCUMENTED_STATUS_CODES = {"A": "Active", "I": "Inactive"}


def _to_raw(row: FlBusinessEntity) -> dict:
    """Build the raw payload shape the verify flow consumes (same as other sources)."""

    status_raw = _DOCUMENTED_STATUS_CODES.get((row.status_raw or "").strip(), row.status_raw)
    return {
        "legal_name": row.entity_name,
        "state": "FL",
        "reg_id": row.entity_id,
        "entity_type": row.entity_type,
        "formation_date": row.formation_date.isoformat() if row.formation_date else None,
        "status_raw": status_raw,
        "registered_agent": {"name": row.agent_name, "address": row.agent_address},
        "officers": [],  # Never populated in the ingested Sunbiz dataset.
        "address": row.principal_address,
        "mailing_address": row.mailing_address,
        "jurisdiction": row.jurisdiction,
        "source_url": row.source_record_url or FL_DATASET_URL,
        "coverage": {"source": "official_open_data", "officers_published": False},
        "source_record": row.raw,
    }


class FloridaOpenDataConnector:
    """SourceConnector backed by the ingested Florida Sunbiz open-data dataset."""

    name = "florida_sos_opendata"
    capabilities = {CAP_ENTITY, CAP_STATUS}
    states = {"FL"}

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def search(self, query: ConnectorQuery, *, limit: int = 25) -> list[RawResult]:
        if query.state and query.state.upper() != "FL":
            return []

        needle = normalize_name(query.name)
        if not needle:
            return []
        with self._session_factory() as session:
            # This table has 11.6M rows. A leading-wildcard CONTAINS can't use
            # the normalized_name index (~50s, confirmed live). A prefix match
            # should be able to, but neither SQLAlchemy's ``.startswith()``
            # (compiles to ``LIKE needle || '%'``, a runtime concatenation that
            # defeats the optimization) nor a plain ``.like(needle + "%")``
            # reliably gets SQLite's planner to use the index on this table --
            # confirmed live, both still took 20-50s depending on the query
            # even after ``ANALYZE``. Forcing the index via ``INDEXED BY``
            # (verified live: ~0.9s vs ~45s) is the only approach that reliably
            # works, and SQLAlchemy's ORM ``.with_hint()`` does not emit it for
            # the SQLite dialect -- so this does the lookup in two steps: a raw
            # indexed query for matching ids, then a primary-key fetch (always
            # fast) for each one.
            id_rows = session.execute(
                text(
                    "SELECT entity_id FROM fl_business_entities "
                    "INDEXED BY ix_fl_business_entities_normalized_name "
                    "WHERE normalized_name LIKE :pattern "
                    "ORDER BY entity_name LIMIT :limit"
                ),
                {"pattern": f"{needle}%", "limit": limit},
            ).all()
            rows = [session.get(FlBusinessEntity, entity_id) for (entity_id,) in id_rows]
            return [
                RawResult(
                    ref=SourceRef(source_name=self.name, state="FL", reg_id=row.entity_id),
                    legal_name=row.entity_name,
                    state="FL",
                    reg_id=row.entity_id,
                    status_raw=row.status_raw,
                    raw=_to_raw(row),
                )
                for row in rows
            ]

    def fetch(self, ref: SourceRef) -> RawRecord:
        with self._session_factory() as session:
            row = session.get(FlBusinessEntity, ref.reg_id)
            if row is None:
                return RawRecord(ref=ref, raw={}, response_code=404)
            return RawRecord(ref=ref, raw=_to_raw(row), response_code=200)

    def health(self) -> SourceHealth:
        with self._session_factory() as session:
            count = session.scalar(select(func.count()).select_from(FlBusinessEntity)) or 0
        if count == 0:
            return SourceHealth(status="degraded", detail="No Florida data ingested yet")
        return SourceHealth(status="healthy", detail=f"{count} FL entities ingested")
