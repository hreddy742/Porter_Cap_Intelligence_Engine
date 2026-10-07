"""Fast, idempotent batch upserts for state staging tables."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from porter_verify.db.base import Base, utcnow


def upsert_staging_rows(
    session: Session,
    model: type[Base],
    rows: Sequence[dict[str, Any]],
) -> None:
    """Upsert a batch by ``entity_id`` without one ORM round-trip per row."""

    if not rows:
        return
    table: Any = model.__table__
    dialect = session.get_bind().dialect.name
    statement: Any
    if dialect == "sqlite":
        statement = sqlite_insert(table).values(list(rows))
    elif dialect == "postgresql":
        statement = pg_insert(table).values(list(rows))
    else:
        for row in rows:
            session.merge(model(**row))
        return

    excluded = statement.excluded
    updates = {
        column.name: getattr(excluded, column.name)
        for column in table.columns
        if column.name not in {"entity_id", "created_at", "updated_at"}
    }
    updates["updated_at"] = utcnow()
    session.execute(
        statement.on_conflict_do_update(index_elements=[table.c.entity_id], set_=updates)
    )
