"""Normalization: turn messy input into canonical, comparable values.

Two jobs, both deterministic and versioned (the version is recorded on each
verification run so results are reproducible):

1. **Name normalization** — lowercase, strip punctuation, canonicalize entity
   suffixes (LLC/Inc/Corp/...), apply a small synonym map. Used for matching and
   for the company ``dedupe_key``.
2. **Status normalization** — map a state's raw status string to the controlled
   ``RegistrationStatus`` vocabulary. Ambiguous/unknown raw values map to
   ``UNKNOWN`` (which the scoring layer treats as a review trigger), never a guess.

Keeping these pure (str in, value out) makes them trivial to test and audit.
"""

from __future__ import annotations

import re

from porter_verify.db.enums import RegistrationStatus

# Bump when the rules below change so runs remain reproducible/comparable.
NORMALIZATION_VERSION = "norm-v1"

# Canonical form for common legal-entity suffixes (after punctuation removal).
_SUFFIX_CANON = {
    "llc": "llc",
    "l l c": "llc",
    "inc": "inc",
    "incorporated": "inc",
    "corp": "corp",
    "corporation": "corp",
    "co": "co",
    "company": "co",
    "ltd": "ltd",
    "limited": "ltd",
    "lp": "lp",
    "llp": "llp",
}

# Token-level synonyms applied before suffix canonicalization.
_SYNONYMS = {
    "st": "street",
    "ave": "avenue",
}

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    """Return a canonical, comparable form of a business name.

    Example: ``"Acme Logistics, L.L.C."`` -> ``"acme logistics llc"``.
    """

    text = name.lower()
    text = text.replace("&", " and ")  # keep '&' as a word, not lost punctuation
    text = text.replace(".", "")  # collapse dotted acronyms: l.l.c. -> llc
    text = _PUNCT_RE.sub(" ", text)  # remaining punctuation -> space
    text = _WS_RE.sub(" ", text).strip()

    tokens = [_SYNONYMS.get(tok, tok) for tok in text.split(" ") if tok]
    tokens = [_SUFFIX_CANON.get(tok, tok) for tok in tokens]
    return " ".join(tokens)


def dedupe_key(home_state: str | None, normalized_name: str) -> str:
    """Build the company dedupe key: ``STATE|normalized_name`` (state upper-cased)."""

    state = (home_state or "").upper()
    return f"{state}|{normalized_name}"


# Raw-status keyword -> normalized status. Checked as case-insensitive substrings,
# most specific first. Versioned via NORMALIZATION_VERSION.
_STATUS_RULES: list[tuple[str, RegistrationStatus]] = [
    ("active", RegistrationStatus.ACTIVE),
    ("in good standing", RegistrationStatus.ACTIVE),
    ("good standing", RegistrationStatus.ACTIVE),
    ("current", RegistrationStatus.ACTIVE),
    ("existing", RegistrationStatus.ACTIVE),
    ("dissolved", RegistrationStatus.DISSOLVED),
    ("terminated", RegistrationStatus.DISSOLVED),
    ("cancelled", RegistrationStatus.DISSOLVED),
    ("canceled", RegistrationStatus.DISSOLVED),
    ("revoked", RegistrationStatus.DISSOLVED),
    ("withdrawn", RegistrationStatus.INACTIVE),
    ("inactive", RegistrationStatus.INACTIVE),
    ("expired", RegistrationStatus.INACTIVE),
    ("delinquent", RegistrationStatus.DELINQUENT),
    ("not in good standing", RegistrationStatus.DELINQUENT),
    ("forfeited", RegistrationStatus.DELINQUENT),
    ("suspended", RegistrationStatus.DELINQUENT),
    ("past due", RegistrationStatus.DELINQUENT),
]


def normalize_status(status_raw: str | None) -> RegistrationStatus:
    """Map a raw per-state status string to the controlled vocabulary.

    Unrecognized or empty values return ``UNKNOWN`` rather than guessing — the
    scoring layer treats UNKNOWN as a human-review trigger.
    """

    if not status_raw or not status_raw.strip():
        return RegistrationStatus.UNKNOWN

    text = status_raw.strip().lower()
    # "not in good standing" must beat "good standing": check longer rules first.
    for keyword, status in sorted(_STATUS_RULES, key=lambda r: -len(r[0])):
        if keyword in text:
            return status
    return RegistrationStatus.UNKNOWN
