"""Tests for conservative entity resolution (plan §11)."""

from __future__ import annotations

from porter_verify.services.entity_resolution import (
    Candidate,
    EntityQuery,
    Outcome,
    name_sim,
    resolve,
    weighted_match,
)


def test_name_sim_identical_is_one() -> None:
    assert name_sim("Acme Logistics LLC", "acme logistics, l.l.c.") == 1.0


def test_name_sim_unrelated_is_low() -> None:
    assert name_sim("Acme Logistics", "Zenith Pharmaceuticals") < 0.3


def test_full_match_auto_accepts() -> None:
    query = EntityQuery(name="Acme Logistics LLC", state="TX", reg_id="TX-1", address="100 Main St")
    candidate = Candidate(
        id="c1", name="Acme Logistics, LLC", state="TX", reg_id="TX-1", address="100 Main St"
    )
    result = resolve(query, [candidate])
    assert result.outcome is Outcome.AUTO_ACCEPT
    assert result.chosen is not None
    assert result.chosen.score >= 0.92


def test_reg_id_name_state_alone_needs_review_not_auto() -> None:
    # Strong but without corroborating address: 0.45 + 0.25 + 0.15 = 0.85 -> review.
    query = EntityQuery(name="Acme Logistics LLC", state="TX", reg_id="TX-1")
    candidate = Candidate(id="c1", name="Acme Logistics LLC", state="TX", reg_id="TX-1")
    result = resolve(query, [candidate])
    assert result.outcome is Outcome.NEEDS_REVIEW


def test_name_alone_never_auto_matches() -> None:
    # Identical name but nothing else: 0.25 * 1.0 = 0.25 -> NO_MATCH. Conservative.
    query = EntityQuery(name="Acme Logistics LLC")
    candidate = Candidate(id="c1", name="Acme Logistics LLC")
    result = resolve(query, [candidate])
    assert result.outcome is Outcome.NO_MATCH


def test_ambiguous_strong_matches_go_to_review() -> None:
    query = EntityQuery(name="Acme LLC", state="TX", reg_id="TX-1", address="100 Main St")
    # Two near-identical candidates -> both score high and within the margin.
    c1 = Candidate(id="c1", name="Acme LLC", state="TX", reg_id="TX-1", address="100 Main St")
    c2 = Candidate(id="c2", name="Acme LLC", state="TX", reg_id="TX-1", address="100 Main St")
    result = resolve(query, [c1, c2])
    assert result.outcome is Outcome.NEEDS_REVIEW


def test_no_candidates_is_no_match() -> None:
    result = resolve(EntityQuery(name="Acme"), [])
    assert result.outcome is Outcome.NO_MATCH
    assert result.chosen is None


def test_components_are_exposed_for_audit() -> None:
    query = EntityQuery(name="Acme LLC", state="TX", reg_id="TX-1")
    scored = weighted_match(query, Candidate(id="c1", name="Acme LLC", state="TX", reg_id="TX-1"))
    assert set(scored.components) == {"reg_id", "name", "state", "address", "agent"}
    assert scored.components["reg_id"] == 1.0


def test_resolution_is_deterministic() -> None:
    query = EntityQuery(name="Acme LLC", state="TX", reg_id="TX-1")
    cands = [Candidate(id="c1", name="Acme LLC", state="TX", reg_id="TX-1")]
    assert resolve(query, cands).chosen.score == resolve(query, cands).chosen.score  # type: ignore[union-attr]
