"""Tests for OFAC refresh job behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from porter_verify.config import get_settings
from porter_verify.services.ofac import get_ofac_metadata_by_name
from porter_verify.services.screening import get_sanctions_list


def test_refresh_ofac_downloads_sdn_and_aliases_and_clears_caches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from porter_verify.services import ofac_refresh

    sdn = tmp_path / "sdn.csv"
    alt = tmp_path / "alt.csv"
    monkeypatch.setenv("PORTER_OFAC_SDN_PATH", str(sdn))
    monkeypatch.setenv("PORTER_OFAC_ALT_PATH", str(alt))
    get_settings.cache_clear()
    get_sanctions_list.cache_clear()
    get_ofac_metadata_by_name.cache_clear()

    class Response:
        def __init__(self, text: str) -> None:
            self.text = text
            self.content = text.encode("utf-8")

        def raise_for_status(self) -> None:
            return None

    responses = [
        Response('306,"BANCO NACIONAL DE CUBA","aka BNC ","CUBA",-0-\n'),
        Response('306,1,"aka","BNC",-0-\n'),
    ]

    def fake_get(url: str, *, follow_redirects: bool, timeout: int) -> Response:
        assert follow_redirects is True
        assert timeout == 60
        return responses.pop(0)

    monkeypatch.setattr(ofac_refresh.httpx, "get", fake_get)
    try:
        assert ofac_refresh.refresh_ofac_files() == (1, 1)
        assert sdn.exists()
        assert alt.exists()
        assert "BNC" in get_sanctions_list()
        assert get_ofac_metadata_by_name()["bnc"] == ("CUBA", True)
    finally:
        get_settings.cache_clear()
        get_sanctions_list.cache_clear()
        get_ofac_metadata_by_name.cache_clear()
