"""Confidence scoring: deterministic, explainable, versioned (plan §12).

This is NOT AI guessing. The same inputs always produce the same output. Each
component score carries the evidence-derived inputs, its value, its weight, an
explanation, and whether it triggers human review. The overall verification status
is derived from explicit rules, not a black-box weighted sum.

ML scoring is deferred until labeled outcomes exist (plan Phase 5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from porter_verify.db.enums import RegistrationStatus, VerificationStatus

# Bump when the rules/weights change so historical runs stay comparable.
SCORING_VERSION = "score-v1"

# Freshness bands, in days (plan §12.1).
FRESH_DAYS = 30
PARTIAL_DAYS = 90

# Entity-match bands (plan §11.3 / §12.2).
STRONG_MATCH = 0.92
LIKELY_MATCH = 0.85
REVIEW_MATCH = 0.75


@dataclass(frozen=True)
class ScoringInput:
    """Evidence-derived inputs to scoring (all come from a verification run)."""

    existence_found: bool
    match_confidence: float
    registration_status: RegistrationStatus
    evidence_age_days: int | None
    source_health: str = "unknown"
    ofac_hit: bool = False


@dataclass(frozen=True)
class ComponentScore:
    component: str
    value: float
    weight: float
    explanation: str
    review_trigger: bool


@dataclass(frozen=True)
class ScoreResult:
    overall_status: VerificationStatus
    match_confidence: float
    components: list[ComponentScore] = field(default_factory=list)
    version: str = SCORING_VERSION

    @property
    def needs_review(self) -> bool:
        return self.overall_status is VerificationStatus.NEEDS_REVIEW or any(
            c.review_trigger for c in self.components
        )


_STATUS_VALUE = {
    RegistrationStatus.ACTIVE: 1.0,
    RegistrationStatus.DELINQUENT: 0.5,
    RegistrationStatus.INACTIVE: 0.2,
    RegistrationStatus.DISSOLVED: 0.0,
    RegistrationStatus.UNKNOWN: 0.0,
}


def _existence_component(inp: ScoringInput) -> ComponentScore:
    found = inp.existence_found
    return ComponentScore(
        component="business_existence",
        value=1.0 if found else 0.0,
        weight=0.30,
        explanation="Found in source registry" if found else "Not found — insufficient evidence",
        review_trigger=not found,
    )


def _match_component(inp: ScoringInput) -> ComponentScore:
    conf = inp.match_confidence
    return ComponentScore(
        component="entity_match",
        value=round(conf, 3),
        weight=0.30,
        explanation=f"Entity-resolution confidence {conf:.2f}",
        review_trigger=conf < STRONG_MATCH,
    )


def _status_component(inp: ScoringInput) -> ComponentScore:
    status = inp.registration_status
    return ComponentScore(
        component="registration_status",
        value=_STATUS_VALUE[status],
        weight=0.20,
        explanation=f"Normalized status: {status.value}",
        review_trigger=status is RegistrationStatus.UNKNOWN,
    )


def _freshness_component(inp: ScoringInput) -> ComponentScore:
    age = inp.evidence_age_days
    if age is None:
        value, explanation = 0.0, "No evidence timestamp"
    elif age < FRESH_DAYS:
        value, explanation = 1.0, f"Fresh evidence ({age}d old)"
    elif age <= PARTIAL_DAYS:
        value, explanation = 0.6, f"Partially stale evidence ({age}d old)"
    else:
        value, explanation = 0.3, f"Stale evidence ({age}d old)"
    return ComponentScore(
        component="data_freshness",
        value=value,
        weight=0.10,
        explanation=explanation,
        review_trigger=age is None or age > PARTIAL_DAYS,
    )


def _source_component(inp: ScoringInput) -> ComponentScore:
    health = inp.source_health.lower()
    value = {"healthy": 1.0, "degraded": 0.5}.get(health, 0.5)
    return ComponentScore(
        component="source_reliability",
        value=value,
        weight=0.10,
        explanation=f"Source health: {health}",
        review_trigger=health == "degraded",
    )


def derive_overall_status(inp: ScoringInput) -> VerificationStatus:
    """Derive the overall verification status from explicit rules (plan §12.2)."""

    if inp.ofac_hit:
        return VerificationStatus.RISK_FLAG
    if not inp.existence_found:
        return VerificationStatus.INSUFFICIENT_EVIDENCE
    if inp.registration_status in (RegistrationStatus.DISSOLVED, RegistrationStatus.DELINQUENT):
        return VerificationStatus.INACTIVE_NOT_ELIGIBLE
    if inp.registration_status is RegistrationStatus.INACTIVE:
        return VerificationStatus.INACTIVE_NOT_ELIGIBLE
    if inp.registration_status is RegistrationStatus.UNKNOWN:
        return VerificationStatus.NEEDS_REVIEW

    # Status is ACTIVE from here.
    fresh = inp.evidence_age_days is not None and inp.evidence_age_days < FRESH_DAYS
    conf = inp.match_confidence
    if conf >= STRONG_MATCH and fresh:
        return VerificationStatus.VERIFIED
    if conf >= LIKELY_MATCH:  # 0.85-0.92, or >=0.92 but stale
        return VerificationStatus.LIKELY_MATCH
    if conf >= REVIEW_MATCH:  # 0.75-0.85
        return VerificationStatus.NEEDS_REVIEW
    return VerificationStatus.INSUFFICIENT_EVIDENCE


def score(inp: ScoringInput) -> ScoreResult:
    """Compute the full, explainable confidence result for a verification run."""

    components = [
        _existence_component(inp),
        _match_component(inp),
        _status_component(inp),
        _freshness_component(inp),
        _source_component(inp),
    ]
    return ScoreResult(
        overall_status=derive_overall_status(inp),
        match_confidence=round(inp.match_confidence, 3),
        components=components,
    )
