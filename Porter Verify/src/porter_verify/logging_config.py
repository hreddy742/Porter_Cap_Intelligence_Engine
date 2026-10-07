"""Structured logging setup.

We use ``structlog`` so every log line carries structured key/value context and
can be emitted as JSON in staging/production (machine-parseable, Sentry-friendly)
or as colorized console output locally.

Security note: never log secrets, raw credentials, or full PII. Log identifiers
(company_id, run_id, actor) instead. Audit-worthy events go through the audit
service, not plain logs.
"""

from __future__ import annotations

import logging

import structlog

from porter_verify.config import Settings, get_settings


def configure_logging(settings: Settings | None = None) -> None:
    """Configure structlog + stdlib logging once at process startup.

    Idempotent enough to call from app startup and from test fixtures.
    """

    settings = settings or get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(format="%(message)s", level=level)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Human-friendly console locally; structured JSON everywhere else.
    renderer: structlog.types.Processor = (
        structlog.dev.ConsoleRenderer()
        if settings.log_console
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger. Prefer module-level ``__name__``."""

    return structlog.get_logger(name)
