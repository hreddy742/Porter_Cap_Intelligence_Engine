"""Tests for structured logging configuration."""

from __future__ import annotations

import structlog

from porter_verify.config import Settings
from porter_verify.logging_config import configure_logging, get_logger


def test_configure_logging_is_callable_and_returns_logger() -> None:
    configure_logging(Settings(_env_file=None))
    log = get_logger("test")
    assert isinstance(log, structlog.typing.BindableLogger)


def test_json_renderer_emits_structured_line(capsys) -> None:
    # JSON mode (non-console) should produce a parseable, key=value-rich line.
    configure_logging(Settings(_env_file=None, log_console=False, log_level="INFO"))
    get_logger("test").info("verification_started", company_id="abc-123")
    out = capsys.readouterr().out
    assert "verification_started" in out
    assert "abc-123" in out
