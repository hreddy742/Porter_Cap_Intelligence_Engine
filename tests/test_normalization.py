"""Tests for the normalization service (name + status)."""

from __future__ import annotations

import pytest

from porter_verify.db.enums import RegistrationStatus
from porter_verify.services.normalization import (
    dedupe_key,
    normalize_name,
    normalize_status,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Acme Logistics, L.L.C.", "acme logistics llc"),
        ("ACME LOGISTICS LLC", "acme logistics llc"),
        ("Acme  Logistics   Incorporated", "acme logistics inc"),
        ("Smith & Sons Co.", "smith and sons co"),
        ("Big Box Corporation", "big box corp"),
    ],
)
def test_normalize_name(raw: str, expected: str) -> None:
    assert normalize_name(raw) == expected


def test_normalize_name_is_idempotent() -> None:
    once = normalize_name("Acme Logistics, L.L.C.")
    assert normalize_name(once) == once


def test_dedupe_key_uppercases_state() -> None:
    assert dedupe_key("tx", "acme logistics llc") == "TX|acme logistics llc"
    assert dedupe_key(None, "acme") == "|acme"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Active", RegistrationStatus.ACTIVE),
        ("In Good Standing", RegistrationStatus.ACTIVE),
        ("Dissolved", RegistrationStatus.DISSOLVED),
        ("Administratively Dissolved", RegistrationStatus.DISSOLVED),
        ("Forfeited - Failed to File", RegistrationStatus.DELINQUENT),
        ("Not in Good Standing", RegistrationStatus.DELINQUENT),
        ("Withdrawn", RegistrationStatus.INACTIVE),
        ("Some Unrecognized State Jargon", RegistrationStatus.UNKNOWN),
        ("", RegistrationStatus.UNKNOWN),
        (None, RegistrationStatus.UNKNOWN),
    ],
)
def test_normalize_status(raw: str | None, expected: RegistrationStatus) -> None:
    assert normalize_status(raw) is expected


def test_not_in_good_standing_beats_good_standing() -> None:
    # The longer, more specific rule must win.
    assert normalize_status("not in good standing") is RegistrationStatus.DELINQUENT
