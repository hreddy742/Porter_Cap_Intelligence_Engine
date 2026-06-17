"""Tests for the confidence scoring model (plan §12)."""

from __future__ import annotations

import pytest

from porter_verify.db.enums import RegistrationStatus, VerificationStatus
from porter_verify.services.scoring import ScoringInput, derive_overall_status, score


def _inp(**overrides: object) -> ScoringInput:
    base: dict[str, object] = {
        "existence_found": True,
        "match_confidence": 0.95,
        "registration_status": RegistrationStatus.ACTIVE,
        "evidence_age_days": 5,
        "source_health": "healthy",
        "ofac_hit": False,
    }
    base.update(overrides)
    return ScoringInput(**base)  # type: ignore[arg-type]


def test_strong_fresh_active_match_is_verified() -> None:
    assert derive_overall_status(_inp()) is VerificationStatus.VERIFIED


def test_strong_but_stale_is_likely_match() -> None:
    assert derive_overall_status(_inp(evidence_age_days=60)) is VerificationStatus.LIKELY_MATCH


def test_mid_confidence_is_likely_match() -> None:
    assert derive_overall_status(_inp(match_confidence=0.88)) is VerificationStatus.LIKELY_MATCH


def test_review_band_confidence_needs_review() -> None:
    assert derive_overall_status(_inp(match_confidence=0.80)) is VerificationStatus.NEEDS_REVIEW


def test_low_confidence_is_insufficient() -> None:
    assert (
        derive_overall_status(_inp(match_confidence=0.50))
        is VerificationStatus.INSUFFICIENT_EVIDENCE
    )


def test_not_found_is_insufficient() -> None:
    assert (
        derive_overall_status(_inp(existence_found=False))
        is VerificationStatus.INSUFFICIENT_EVIDENCE
    )


@pytest.mark.parametrize(
    "status",
    [RegistrationStatus.DISSOLVED, RegistrationStatus.DELINQUENT, RegistrationStatus.INACTIVE],
)
def test_inactive_statuses_are_not_eligible(status: RegistrationStatus) -> None:
    assert (
        derive_overall_status(_inp(registration_status=status))
        is VerificationStatus.INACTIVE_NOT_ELIGIBLE
    )


def test_unknown_status_needs_review() -> None:
    assert (
        derive_overall_status(_inp(registration_status=RegistrationStatus.UNKNOWN))
        is VerificationStatus.NEEDS_REVIEW
    )


def test_ofac_hit_overrides_everything() -> None:
    # Even a perfect entity match is a RISK_FLAG if OFAC matches.
    assert derive_overall_status(_inp(ofac_hit=True)) is VerificationStatus.RISK_FLAG


def test_score_is_deterministic() -> None:
    assert score(_inp()) == score(_inp())


def test_score_exposes_all_components() -> None:
    result = score(_inp())
    names = {c.component for c in result.components}
    assert names == {
        "business_existence",
        "entity_match",
        "registration_status",
        "data_freshness",
        "source_reliability",
    }
    assert result.version == "score-v1"


def test_needs_review_property_flags_low_match() -> None:
    # match_confidence 0.80 < 0.92 -> entity_match component triggers review.
    assert score(_inp(match_confidence=0.80)).needs_review is True
