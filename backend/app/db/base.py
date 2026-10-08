"""SQLAlchemy declarative base and shared column helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """Timezone-aware UTC now. All timestamps use this."""
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    """Treat a naive datetime as UTC.

    SQLite hands back naive datetimes even for timezone-aware columns, so any
    comparison against `utcnow()` would otherwise fail forever on SQLite while
    passing on PostgreSQL.
    """
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        pk = getattr(self, "id", None)
        return f"<{type(self).__name__} id={pk}>"
