"""Users and RBAC roles."""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from porter_verify.db.base import Base, TimestampMixin, uuid_pk


class Role(Base, TimestampMixin):
    """An RBAC role with a list of permission strings (least privilege)."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Permission strings, e.g. ["company:read", "review:write"]. JSON keeps this
    # portable across SQLite (tests) and Postgres (prod).
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="role")


class User(Base, TimestampMixin):
    """An internal Porter user, authenticated via SSO in production."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    # Subject id from the SSO provider (OIDC ``sub``); null until first SSO login.
    sso_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    role_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roles.id"))
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    role: Mapped[Role | None] = relationship(back_populates="users")
