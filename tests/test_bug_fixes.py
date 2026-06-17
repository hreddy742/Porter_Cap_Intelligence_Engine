"""Regression tests for bugs found in the bug sweep."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from porter_verify.connectors.base import (
    ConnectorQuery,
    ConnectorRegistry,
    RawRecord,
    RawResult,
    SourceHealth,
    SourceRef,
)
from porter_verify.connectors.factory import build_default_registry
from porter_verify.db.enums import IdentifierType, RegistrationStatus, VerificationStatus
from porter_verify.db.models import CompanyIdentifier, CompanyOfficer
from porter_verify.services.companies import upsert_company
from porter_verify.services.evidence import EvidenceStore
from porter_verify.services.queries import search_companies
from porter_verify.workers.verify_flow import run_verification


def _store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(tmp_path)


# --- #4: fetch-404 must not fabricate a company from the query --------------


class _SearchHitButFetch404Connector:
    """Search returns a hit, but the detail fetch 404s (record vanished)."""

    name = "flaky"
    capabilities = {"status", "entity"}
    states: set[str] = set()

    def search(self, query: ConnectorQuery) -> list[RawResult]:
        ref = SourceRef(source_name=self.name, state="TX", reg_id="TX-1")
        return [
            RawResult(
                ref=ref,
                legal_name="Ghost Co",
                state="TX",
                reg_id="TX-1",
                status_raw="Active",
                raw={"legal_name": "Ghost Co", "state": "TX", "reg_id": "TX-1"},
            )
        ]

    def fetch(self, ref: SourceRef) -> RawRecord:
        return RawRecord(ref=ref, raw={}, response_code=404)

    def health(self) -> SourceHealth:
        return SourceHealth(status="healthy")


def test_fetch_404_does_not_fabricate_company(tmp_path: Path, db_session: Session) -> None:
    registry = ConnectorRegistry()
    registry.register(_SearchHitButFetch404Connector())

    outcome = run_verification(
        db_session, registry=registry, evidence_store=_store(tmp_path), name="Ghost Co", state="TX"
    )
    assert outcome.verification_status is VerificationStatus.INSUFFICIENT_EVIDENCE
    assert outcome.company_id is None  # no fabricated company spine


# --- #2: state registration number recorded as an identifier ---------------


def test_verify_records_state_reg_identifier(tmp_path: Path, db_session: Session) -> None:
    run_verification(
        db_session,
        registry=build_default_registry(),
        evidence_store=_store(tmp_path),
        name="Acme Logistics LLC",
        state="TX",
    )
    ident = db_session.scalar(
        select(CompanyIdentifier).where(CompanyIdentifier.id_type == IdentifierType.STATE_REG)
    )
    assert ident is not None
    assert ident.id_value == "TX-0801234"


# --- #5: re-verification must not duplicate officers -----------------------


def test_reverify_does_not_duplicate_officers(tmp_path: Path, db_session: Session) -> None:
    registry = build_default_registry()
    store = _store(tmp_path)
    for _ in range(2):
        run_verification(
            db_session,
            registry=registry,
            evidence_store=store,
            name="Acme Logistics LLC",
            state="TX",
        )
    # Acme has exactly one officer in the fixture; two runs must not double it.
    count = db_session.scalar(select(func.count()).select_from(CompanyOfficer))
    assert count == 1


# --- #3: search must not match everything on a punctuation-only query ------


def test_search_punctuation_query_matches_nothing(db_session: Session) -> None:
    upsert_company(
        db_session,
        legal_name="Acme Logistics LLC",
        home_state="TX",
        status=RegistrationStatus.ACTIVE,
    )
    db_session.commit()

    assert search_companies(db_session, query="...") == []  # would have matched all
    assert len(search_companies(db_session, query="acme")) == 1  # real query still works
