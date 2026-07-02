"""Application configuration.

All runtime configuration is read from environment variables (12-factor style)
so the same image runs unchanged across local / staging / production. Secrets are
never hardcoded; production supplies them via a secrets manager.

Usage:
    from porter_verify.config import get_settings
    settings = get_settings()
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment. Drives safety defaults (e.g. log format)."""

    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Strongly-typed application settings, loaded from env vars / ``.env``.

    Every field is validated by Pydantic at startup, so a misconfigured
    environment fails loudly and immediately rather than at first use.
    """

    model_config = SettingsConfigDict(
        env_prefix="PORTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- application -------------------------------------------------------
    env: Environment = Environment.LOCAL
    log_level: str = "INFO"
    log_console: bool = True
    scheduler_enabled: bool = True

    # --- database ---------------------------------------------------------
    # Default points at the docker-compose Postgres. Tests override this with
    # an isolated SQLite URL, so the default is safe to keep here.
    database_url: str = "postgresql+psycopg://porter:porter@localhost:5432/porter_verify"

    # --- evidence store ---------------------------------------------------
    evidence_dir: str = "./evidence_store"

    # --- OFAC sanctions list ----------------------------------------------
    # Local copy of the official OFAC SDN CSV (populated by scripts/refresh_ofac.py).
    # When absent, screening falls back to a small bundled fixture.
    ofac_sdn_path: str = "./data/ofac_sdn.csv"
    ofac_alt_path: str = "./data/ofac_alt.csv"
    fl_ucc_zip_dir: str = "./data/florida_ucc"

    # --- API authentication -----------------------------------------------
    # Comma-separated triples: email:role:key
    # Example: alice@portercap.net:sales:sk-v1-s-abc123,bob@portercap.net:admin:sk-v1-a-xyz789
    # Blank in local/test — all routes are protected; populate in .env for real dev use.
    api_keys: str = Field(default="", repr=False)

    # --- CORS for production -----------------------------------------------
    # Comma-separated allowed origins for the browser frontend in staging/prod.
    # Example: https://verify.portercap.net,https://verify-staging.portercap.net
    allowed_origins: str = ""

    # --- vendor / integration credential references -----------------------
    # Blank locally => the mock connector is used. Real values are secret-manager
    # references in production, surfaced to the process as env vars at runtime.
    sos_vendor_api_key: str = Field(default="", repr=False)
    salesforce_client_id: str = Field(default="", repr=False)
    salesforce_client_secret: str = Field(default="", repr=False)
    salesforce_instance_url: str = ""

    # --- observability ----------------------------------------------------
    sentry_dsn: str = Field(default="", repr=False)

    @property
    def is_production(self) -> bool:
        return self.env is Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so configuration is parsed once per process. Tests can clear the
    cache via ``get_settings.cache_clear()`` after mutating the environment.
    """

    return Settings()
