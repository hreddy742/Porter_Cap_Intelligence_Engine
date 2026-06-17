"""Tests for real OFAC SDN parsing and its use in screening."""

from __future__ import annotations

from pathlib import Path

import pytest

from porter_verify.config import get_settings
from porter_verify.connectors.ofac import load_sdn_names, parse_sdn_csv
from porter_verify.services import screening
from porter_verify.services.screening import get_sanctions_list, screen

# A realistic slice of the official OFAC SDN CSV (headerless; field 1 = name).
SAMPLE_SDN = (
    '36,"AEROCARIBBEAN AIRLINES",-0- ,"CUBA",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0-\n'
    '173,"ANGLO-CARIBBEAN CO., LTD.",-0- ,"CUBA",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0-\n'
    '306,"BANCO NACIONAL DE CUBA","aka BNC ","CUBA",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0-\n'
)


def test_parse_extracts_names_handling_quoted_commas() -> None:
    names = parse_sdn_csv(SAMPLE_SDN)
    assert names == [
        "AEROCARIBBEAN AIRLINES",
        "ANGLO-CARIBBEAN CO., LTD.",  # comma inside quotes preserved
        "BANCO NACIONAL DE CUBA",
    ]


def test_parse_skips_blank_and_placeholder_names() -> None:
    text = '1,-0- ,-0- ,"X"\n2,"Real Name Inc",-0- ,"Y"\n'
    assert parse_sdn_csv(text) == ["Real Name Inc"]


def test_load_sdn_names_from_file(tmp_path: Path) -> None:
    f = tmp_path / "sdn.csv"
    f.write_text(SAMPLE_SDN, encoding="utf-8")
    assert "BANCO NACIONAL DE CUBA" in load_sdn_names(f)


def test_screening_hits_against_real_format_list() -> None:
    names = parse_sdn_csv(SAMPLE_SDN)
    result = screen("Banco Nacional de Cuba", sanctions_list=names)
    assert result.hit is True
    assert result.matches[0].sanctioned_name == "BANCO NACIONAL DE CUBA"


def test_get_sanctions_list_uses_file_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "ofac.csv"
    f.write_text(SAMPLE_SDN, encoding="utf-8")
    monkeypatch.setenv("PORTER_OFAC_SDN_PATH", str(f))
    get_settings.cache_clear()
    get_sanctions_list.cache_clear()
    try:
        names = get_sanctions_list()
        assert "AEROCARIBBEAN AIRLINES" in names
    finally:
        # Reset caches so other tests fall back to the bundled fixture.
        get_settings.cache_clear()
        get_sanctions_list.cache_clear()


def test_get_sanctions_list_falls_back_to_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_OFAC_SDN_PATH", "/nonexistent/path/ofac.csv")
    get_settings.cache_clear()
    get_sanctions_list.cache_clear()
    try:
        assert get_sanctions_list() == screening._FIXTURE_LIST
    finally:
        get_settings.cache_clear()
        get_sanctions_list.cache_clear()
