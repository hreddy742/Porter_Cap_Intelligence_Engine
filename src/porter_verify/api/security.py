"""Authentication boundary and role-based access control (RBAC).

Every request must carry an ``Authorization: Bearer <key>`` header where
``<key>`` is one of the keys declared in ``PORTER_API_KEYS`` (env var,
format: ``email:role:key,...``).  The key is the authoritative identity
source — there is no way to escalate privileges by spoofing headers.

``require_roles`` and ``CurrentUser`` are unchanged from the previous
design; all existing RBAC guards continue to work without modification.
The only seam that changed is *how* ``CurrentUser`` is resolved.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from porter_verify.config import get_settings
from porter_verify.logging_config import get_logger

log = get_logger(__name__)

VALID_ROLES = {"sales", "underwriter", "ops", "admin", "compliance"}

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    email: str
    role: str


@lru_cache(maxsize=1)
def _build_key_map() -> dict[str, CurrentUser]:
    """Parse PORTER_API_KEYS into a {key: CurrentUser} lookup table.

    Called once per process (lru_cache).  Tests clear with
    ``_build_key_map.cache_clear()`` after mutating PORTER_API_KEYS.

    Expected format (comma-separated triples):
        alice@portercap.net:sales:sk-v1-s-abc123,bob@portercap.net:admin:sk-v1-a-xyz789
    """
    raw = get_settings().api_keys.strip()
    if not raw:
        return {}

    result: dict[str, CurrentUser] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) != 3:
            log.warning("api_key_parse_error", entry=entry[:20], reason="expected email:role:key")
            continue
        email, role, key = (p.strip() for p in parts)
        role = role.lower()
        if role not in VALID_ROLES:
            log.warning("api_key_parse_error", entry=entry[:20], reason=f"unknown role {role!r}")
            continue
        if not key:
            log.warning("api_key_parse_error", entry=entry[:20], reason="empty key")
            continue
        result[key] = CurrentUser(email=email.lower(), role=role)

    log.info("api_key_map_loaded", count=len(result))
    return result


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> CurrentUser:
    """Resolve the caller from a Bearer API key, or raise 401."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide: Authorization: Bearer <api-key>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = _build_key_map().get(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed: str) -> Callable[[CurrentUser], CurrentUser]:
    """Dependency factory: allow only the given roles (admin is always allowed)."""
    permitted = {*allowed, "admin"}

    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in permitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user

    return _dependency
