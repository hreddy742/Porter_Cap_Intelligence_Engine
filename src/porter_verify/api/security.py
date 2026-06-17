"""Authentication boundary and role-based access control (RBAC).

MVP auth is a placeholder boundary: the caller's identity and role arrive in the
``X-User-Email`` / ``X-User-Role`` headers (in production these are issued by SSO
behind a gateway — the rest of the code is unchanged). Every protected route runs
through ``require_roles`` so least-privilege is enforced in one place.

This is deliberately simple and inspectable; the security model is documented in
docs/security.md and is the seam where real SSO/JWT validation plugs in.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

# The five internal roles from the plan (§2.1). Compliance is read-only.
VALID_ROLES = {"sales", "underwriter", "ops", "admin", "compliance"}


@dataclass(frozen=True)
class CurrentUser:
    email: str
    role: str


def get_current_user(
    x_user_email: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
) -> CurrentUser:
    """Resolve the caller from auth headers, or 401 if missing/invalid."""

    if not x_user_email or not x_user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    role = x_user_role.strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown role.")
    return CurrentUser(email=x_user_email.strip().lower(), role=role)


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
