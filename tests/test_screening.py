"""Tests for OFAC sanctions screening."""

from __future__ import annotations

from porter_verify.services.screening import screen


def test_clean_name_is_not_a_hit() -> None:
    result = screen("Acme Logistics LLC")
    assert result.hit is False
    assert result.matches == []


def test_sanctioned_name_is_a_hit() -> None:
    result = screen("Specially Designated National Corp")
    assert result.hit is True
    assert result.matches[0].sanctioned_name == "Specially Designated National Corp"
    assert result.matches[0].score >= result.threshold


def test_threshold_is_respected() -> None:
    # An impossible threshold yields no hits even on an exact name.
    result = screen("Sanctioned Trading Company", threshold=1.01)
    assert result.hit is False


def test_custom_sanctions_list() -> None:
    result = screen("Evil Corp", sanctions_list=["Evil Corp"])
    assert result.hit is True


def test_result_records_version_for_audit() -> None:
    assert screen("Acme").version == "ofac-v1"
