"""Tests for application configuration loading and validation."""

from __future__ import annotations

import pytest

from porter_verify.config import Environment, Settings, get_settings


def test_defaults_are_safe_for_local() -> None:
    settings = Settings(_env_file=None)
    assert settings.env is Environment.LOCAL
    assert settings.is_production is False
    # No secrets should be baked into defaults.
    assert settings.sos_vendor_api_key == ""
    assert settings.salesforce_client_secret == ""


def test_env_prefix_is_honored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_ENV", "production")
    monkeypatch.setenv("PORTER_LOG_LEVEL", "WARNING")
    settings = Settings(_env_file=None)
    assert settings.env is Environment.PRODUCTION
    assert settings.is_production is True
    assert settings.log_level == "WARNING"


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_ENV", "not-a-real-env")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_secrets_are_not_shown_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_SOS_VENDOR_API_KEY", "super-secret-value")
    settings = Settings(_env_file=None)
    assert "super-secret-value" not in repr(settings)


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
