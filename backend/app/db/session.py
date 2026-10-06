"""Engine, session factory, and schema creation.

SQLite for the MVP. `DATABASE_URL` switches to PostgreSQL later with no other
code change (SPEC §18).

Migrations: the MVP uses `create_all` on startup. Add Alembic when the schema
starts changing in production.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base

logger = logging.getLogger(__name__)


def _build_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url

    if url.startswith("sqlite"):
        path = settings.database_path
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            future=True,
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _record):  # pragma: no cover - driver callback
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        return engine

    return create_engine(url, future=True, pool_pre_ping=True)


engine: Engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create any missing tables."""
    from app.models import challenge, discovery, user, user_preference  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database ready at %s", get_settings().database_url)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def reset_engine_for_tests() -> None:
    """Testing hook — rebind to an in-memory database."""
    global engine, SessionLocal
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, future=True)
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(bind=engine)


def database_file() -> Path:
    return get_settings().database_path
