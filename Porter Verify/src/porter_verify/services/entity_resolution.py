"""Entity resolution: conservative matching for financial services.

Principle (plan §11): a false match is worse than a miss. Fuzzy similarity may
*surface* candidates for human review, but the system NEVER auto-merges on fuzzy
name alone. Auto-accept requires a strong, unambiguous match.

The weighted-match formula and thresholds come straight from the plan:

    score = 0.45*exact(reg_id) + 0.25*name_sim + 0.15*state_eq
          + 0.10*addr_sim + 0.05*agent_sim

    >= 0.92 and unambiguous -> AUTO_ACCEPT
    0.75 .. 0.92            -> NEEDS_REVIEW
    multiple within 0.05    -> NEEDS_REVIEW
    < 0.75                  -> NO_MATCH (never a forced guess)

All comparison is done on normalized values, so callers pass raw strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from porter_verify.services.normalization import normalize_name

RESOLUTION_VERSION = "resolve-v1"

AUTO_ACCEPT_THRESHOLD = 0.92
REVIEW_THRESHOLD = 0.75
AMBIGUITY_MARGIN = 0.05


class Outcome(StrEnum):
    AUTO_ACCEPT = "auto_accept"
    NEEDS_REVIEW = "needs_review"
    NO_MATCH = "no_match"


@dataclass(frozen=True)
class EntityQuery:
    """The entity we are trying to resolve (raw input; normalized internally)."""

    name: str
    state: str | None = None
    reg_id: str | None = None
    address: str | None = None
    agent: str | None = None


@dataclass(frozen=True)
class Candidate:
    """A possible match (e.g. an existing company or a source search result)."""

    id: str
    name: str
    state: str | None = None
    reg_id: str | None = None
    address: str | None = None
    agent: str | None = None


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: Candidate
    score: float
    components: dict[str, float]


@dataclass(frozen=True)
class Resolution:
    outcome: Outcome
    chosen: ScoredCandidate | None
    candidates: list[ScoredCandidate] = field(default_factory=list)


def _trigrams(text: str) -> set[str]:
    padded = f"  {text} "
    return {padded[i : i + 3] for i in range(len(padded) - 2)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _token_sim(a_tokens: set[str], b_tokens: set[str]) -> float:
    """Token similarity that tolerates extra tokens (e.g. a missing 'LLC' suffix).

    Averages Jaccard (penalizes extra tokens) with containment (|∩| / smaller set,
    which is 1.0 when one name's tokens are a subset of the other's). This keeps an
    exact core name + suffix difference in the review band rather than dismissing it.
    """

    if not a_tokens or not b_tokens:
        return 0.0
    inter = len(a_tokens & b_tokens)
    jaccard = inter / len(a_tokens | b_tokens)
    containment = inter / min(len(a_tokens), len(b_tokens))
    return (jaccard + containment) / 2


def name_sim(a: str, b: str) -> float:
    """Similarity of two names in 0.0..1.0 (normalized first).

    Average of a containment-aware token similarity and character-trigram Jaccard.
    """

    na, nb = normalize_name(a), normalize_name(b)
    if na == nb:
        return 1.0
    token_sim = _token_sim(set(na.split()), set(nb.split()))
    tri_sim = _jaccard(_trigrams(na), _trigrams(nb))
    return round((token_sim + tri_sim) / 2, 4)


def _exact(a: str | None, b: str | None) -> float:
    if a and b and a.strip().lower() == b.strip().lower():
        return 1.0
    return 0.0


def _state_eq(a: str | None, b: str | None) -> float:
    if a and b and a.strip().upper() == b.strip().upper():
        return 1.0
    return 0.0


def _optional_sim(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return name_sim(a, b)


def weighted_match(query: EntityQuery, candidate: Candidate) -> ScoredCandidate:
    """Compute the weighted match score and per-signal component breakdown."""

    components = {
        "reg_id": _exact(query.reg_id, candidate.reg_id),
        "name": name_sim(query.name, candidate.name),
        "state": _state_eq(query.state, candidate.state),
        "address": _optional_sim(query.address, candidate.address),
        "agent": _optional_sim(query.agent, candidate.agent),
    }
    score = (
        0.45 * components["reg_id"]
        + 0.25 * components["name"]
        + 0.15 * components["state"]
        + 0.10 * components["address"]
        + 0.05 * components["agent"]
    )
    return ScoredCandidate(
        candidate=candidate, score=round(min(score, 1.0), 4), components=components
    )


def rank_results(query: EntityQuery, candidates: list[Candidate]) -> Resolution:
    """Rank source search results against a SPARSE query (name + optional state).

    The verify-from-name flow only has the user's name and state — not a reg_id —
    so the full ``weighted_match`` formula (which puts 0.45 on reg_id) doesn't
    apply. Here confidence is driven by name similarity, gated by state agreement:
    a state mismatch halves the score. Thresholds (auto/review) are the same, so an
    exact legal-name + state match can auto-accept while a partial name routes to
    review. Ambiguity (two close results) always routes to review.
    """

    if not candidates:
        return Resolution(outcome=Outcome.NO_MATCH, chosen=None, candidates=[])

    scored_list: list[ScoredCandidate] = []
    for c in candidates:
        name_score = name_sim(query.name, c.name)
        state_ok = _state_eq(query.state, c.state) == 1.0 or query.state is None
        score = name_score if state_ok else name_score * 0.5
        scored_list.append(
            ScoredCandidate(
                candidate=c,
                score=round(score, 4),
                components={"name": name_score, "state_ok": float(state_ok)},
            )
        )

    scored = sorted(scored_list, key=lambda sc: sc.score, reverse=True)
    top = scored[0]
    runner_up = scored[1] if len(scored) > 1 else None
    ambiguous = runner_up is not None and (top.score - runner_up.score) <= AMBIGUITY_MARGIN

    # ``chosen`` is always the best record found, so the flow can record what it
    # saw; the outcome reflects how confident we are it's the right entity.
    if top.score >= AUTO_ACCEPT_THRESHOLD and not ambiguous:
        outcome = Outcome.AUTO_ACCEPT
    elif top.score >= REVIEW_THRESHOLD:
        outcome = Outcome.NEEDS_REVIEW
    else:
        outcome = Outcome.NO_MATCH
    return Resolution(outcome=outcome, chosen=top, candidates=scored[:5])


def resolve(query: EntityQuery, candidates: list[Candidate]) -> Resolution:
    """Resolve ``query`` against ``candidates`` using conservative thresholds.

    NOTE: The live verification flow uses ``rank_results()`` (sparse/name-only path).
    This function is the full weighted-match path (requires reg_id, address, agent)
    and is available for reg_id-based lookups once that capability is wired up.
    """

    if not candidates:
        return Resolution(outcome=Outcome.NO_MATCH, chosen=None, candidates=[])

    scored = sorted(
        (weighted_match(query, c) for c in candidates),
        key=lambda sc: sc.score,
        reverse=True,
    )
    top = scored[0]
    runner_up = scored[1] if len(scored) > 1 else None
    ambiguous = runner_up is not None and (top.score - runner_up.score) <= AMBIGUITY_MARGIN

    # Auto-accept only on a strong AND unambiguous top match.
    if top.score >= AUTO_ACCEPT_THRESHOLD and not ambiguous:
        return Resolution(outcome=Outcome.AUTO_ACCEPT, chosen=top, candidates=scored[:5])

    # Anything plausible (>= 0.75) goes to human review — this also catches the
    # ">=0.92 but ambiguous" case, which falls through from above. Two sub-0.75
    # candidates that happen to be close are treated as NO_MATCH, not review:
    # there is nothing worth disambiguating.
    if top.score >= REVIEW_THRESHOLD:
        return Resolution(outcome=Outcome.NEEDS_REVIEW, chosen=top, candidates=scored[:5])

    return Resolution(outcome=Outcome.NO_MATCH, chosen=None, candidates=scored[:5])
