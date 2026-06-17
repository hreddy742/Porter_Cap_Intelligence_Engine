"""The verification flow — the end-to-end heart of Porter Verify (plan §9.2).

Sequence for one run:

    resolve connector -> search -> store raw -> rank candidates -> fetch ->
    store raw + evidence -> normalize status -> OFAC screen -> upsert company +
    children -> score -> persist scores -> finalize run -> audit

Every step preserves provenance and evidence. Failure paths (no connector, source
outage, no results) finish the run cleanly with an explainable status and an audit
entry — never a crash, never a fabricated result, never a charge for an outage.

The flow is dependency-injected (session, registry, evidence store) so it is fully
testable offline with the mock connector.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from porter_verify.connectors.base import (
    CAP_STATUS,
    ConnectorQuery,
    ConnectorRegistry,
    SourceUnavailableError,
)
from porter_verify.db.enums import EvidenceType, RunStatus, VerificationStatus
from porter_verify.db.models import ConfidenceScore, ErrorLog, RawSourceEvent, VerificationRun
from porter_verify.logging_config import get_logger
from porter_verify.services import companies
from porter_verify.services.audit import record_audit
from porter_verify.services.entity_resolution import Candidate, EntityQuery, Outcome, rank_results
from porter_verify.services.evidence import EvidenceStore, canonical_json_hash
from porter_verify.services.normalization import normalize_status
from porter_verify.services.scoring import SCORING_VERSION, ScoringInput, score
from porter_verify.services.screening import screen

log = get_logger(__name__)


@dataclass
class VerifyOutcome:
    """The result of a verification run, returned to the API/caller."""

    run_id: uuid.UUID
    run_status: RunStatus
    verification_status: VerificationStatus | None
    company_id: uuid.UUID | None
    match_confidence: float | None
    message: str


def _finalize(
    session: Session,
    run: VerificationRun,
    *,
    run_status: RunStatus,
    verification_status: VerificationStatus | None,
    actor: str,
    company_id: uuid.UUID | None,
    message: str,
) -> VerifyOutcome:
    """Set terminal run fields, write an audit entry, and commit."""

    from porter_verify.db.base import utcnow

    run.status = run_status
    run.verification_status = verification_status
    run.finished_at = utcnow()
    run.company_id = company_id
    record_audit(
        session,
        actor=actor,
        action="run.finished",
        entity_type="verification_run",
        entity_id=str(run.id),
        after={
            "run_status": run_status.value,
            "verification_status": getattr(verification_status, "value", None),
        },
    )
    session.commit()
    log.info(
        "verification_finished",
        run_id=str(run.id),
        run_status=run_status.value,
        verification_status=getattr(verification_status, "value", None),
    )
    return VerifyOutcome(
        run_id=run.id,
        run_status=run_status,
        verification_status=verification_status,
        company_id=company_id,
        match_confidence=float(run.match_confidence) if run.match_confidence is not None else None,
        message=message,
    )


def run_verification(
    session: Session,
    *,
    registry: ConnectorRegistry,
    evidence_store: EvidenceStore,
    name: str,
    state: str | None = None,
    actor: str = "system",
    trigger: str = "manual",
) -> VerifyOutcome:
    """Run the full verification flow for a business name (+ optional state)."""

    run = VerificationRun(status=RunStatus.RUNNING, trigger=trigger, score_version=SCORING_VERSION)
    session.add(run)
    session.flush()
    log.info("verification_started", run_id=str(run.id), name=name, state=state)

    # 1. Pick a connector that can report status for this state.
    connector = registry.select(state=state, capability=CAP_STATUS)
    if connector is None:
        session.add(
            ErrorLog(
                run_id=run.id, error_type="no_connector", message=f"No source for state={state}"
            )
        )
        return _finalize(
            session,
            run,
            run_status=RunStatus.SOURCE_UNAVAILABLE,
            verification_status=VerificationStatus.INSUFFICIENT_EVIDENCE,
            actor=actor,
            company_id=None,
            message="No data source available for this state.",
        )

    source = companies.get_or_create_source(
        session,
        name=connector.name,
        capabilities=sorted(connector.capabilities),
        states=sorted(connector.states),
    )

    # 2. Search the source. An outage finishes the run without charge.
    try:
        results = connector.search(ConnectorQuery(name=name, state=state))
    except SourceUnavailableError as exc:
        session.add(
            ErrorLog(
                source_id=source.id,
                run_id=run.id,
                error_type="source_unavailable",
                message=str(exc),
            )
        )
        return _finalize(
            session,
            run,
            run_status=RunStatus.SOURCE_UNAVAILABLE,
            verification_status=VerificationStatus.INSUFFICIENT_EVIDENCE,
            actor=actor,
            company_id=None,
            message="The data source is temporarily unavailable. No charge incurred.",
        )

    # Preserve the verbatim search response before any parsing.
    search_payload = {"query": {"name": name, "state": state}, "results": [r.raw for r in results]}
    session.add(
        RawSourceEvent(
            verification_run_id=run.id,
            source_id=source.id,
            request={"name": name, "state": state},
            response_blob=search_payload,
            response_code=200,
            raw_hash=canonical_json_hash(search_payload),
            cost_credits=float(source.cost_per_lookup),
        )
    )

    # 3. No results -> insufficient evidence (never a fabricated match).
    if not results:
        return _finalize(
            session,
            run,
            run_status=RunStatus.COMPLETED,
            verification_status=VerificationStatus.INSUFFICIENT_EVIDENCE,
            actor=actor,
            company_id=None,
            message="No matching business record was found.",
        )

    # 4. Rank candidates against the (sparse) query to pick the right record.
    candidates = [
        Candidate(
            id=r.reg_id,
            name=r.legal_name,
            state=r.state,
            reg_id=r.reg_id,
            address=r.raw.get("address"),
        )
        for r in results
    ]
    resolution = rank_results(EntityQuery(name=name, state=state), candidates)
    chosen = resolution.chosen
    assert chosen is not None  # rank_results always returns a chosen when results exist
    match_confidence = chosen.score
    chosen_result = next(r for r in results if r.reg_id == chosen.candidate.reg_id)

    # 5. Fetch the full record, preserve raw + capture immutable evidence.
    record = connector.fetch(chosen_result.ref)
    session.add(
        RawSourceEvent(
            verification_run_id=run.id,
            source_id=source.id,
            request={"reg_id": chosen_result.reg_id, "state": chosen_result.state},
            response_blob=record.raw,
            response_code=record.response_code,
            latency_ms=record.latency_ms,
            raw_hash=canonical_json_hash(record.raw),
            cost_credits=float(source.cost_per_lookup),
        )
    )
    evidence_store.store(
        session,
        verification_run_id=run.id,
        evidence_type=EvidenceType.RAW_JSON,
        content=json.dumps(record.raw, sort_keys=True).encode("utf-8"),
        source_url=record.raw.get("source_url"),
    )

    raw = record.raw
    status_normalized = normalize_status(raw.get("status_raw"))
    formation = _parse_iso_date(raw.get("formation_date"))

    # 6. OFAC screening on the entity and its officers.
    officers: list[dict] = raw.get("officers") or []
    entity_hit = screen(raw.get("legal_name", name)).hit
    screened = {o["name"]: screen(o["name"]).hit for o in officers if o.get("name")}
    ofac_hit = entity_hit or any(screened.values())

    # 7. Persist the canonical company + children.
    company = companies.upsert_company(
        session,
        legal_name=raw.get("legal_name", name),
        home_state=raw.get("state", state),
        status=status_normalized,
        formation_date=formation,
    )
    registration = companies.add_registration(
        session,
        company=company,
        state=raw.get("state", state or ""),
        state_entity_id=raw.get("reg_id", chosen_result.reg_id),
        entity_type=raw.get("entity_type"),
        formation_date=formation,
        status_raw=raw.get("status_raw"),
        status_normalized=status_normalized,
        source_id=source.id,
    )
    agent = raw.get("registered_agent") or {}
    companies.add_registered_agent(
        session,
        registration=registration,
        agent_name=agent.get("name"),
        agent_address=agent.get("address"),
        source_id=source.id,
    )
    companies.add_officers(
        session,
        company=company,
        officers=officers,
        source_id=source.id,
        screened={name: hit for name, hit in screened.items()},
    )

    # 8. Score (evidence just captured => 0 days old) and derive overall status.
    result = score(
        ScoringInput(
            existence_found=True,
            match_confidence=match_confidence,
            registration_status=status_normalized,
            evidence_age_days=0,
            source_health=connector.health().status,
            ofac_hit=ofac_hit,
        )
    )
    overall = result.overall_status
    # Ambiguous / non-auto resolution must not present as fully verified.
    if resolution.outcome is not Outcome.AUTO_ACCEPT and overall is VerificationStatus.VERIFIED:
        overall = VerificationStatus.NEEDS_REVIEW

    for component in result.components:
        session.add(
            ConfidenceScore(
                verification_run_id=run.id,
                component=component.component,
                value=component.value,
                weight=component.weight,
                explanation=component.explanation,
            )
        )

    run.match_confidence = match_confidence
    run.risk_score = 1.0 if ofac_hit else 0.0

    return _finalize(
        session,
        run,
        run_status=RunStatus.COMPLETED,
        verification_status=overall,
        actor=actor,
        company_id=company.id,
        message=f"Verification complete: {overall.value}.",
    )


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
