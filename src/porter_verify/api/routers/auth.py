"""Auth utility endpoint.

GET /auth/me validates a Bearer API key and returns the caller's identity
so the frontend can populate its user state after the user enters a new key.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from porter_verify.api.security import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    """Return the email and role bound to the supplied API key."""
    return {"email": user.email, "role": user.role}
