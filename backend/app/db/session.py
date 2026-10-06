"""Engine, session factory, and schema creation.

SQLite for the MVP. `DATABASE_URL` switches to PostgreSQL later with no other
code change (SPEC §18).

Migrations: the MVP uses `create_all` on startup. Add Alembic when the schema
starts changing in production.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _journal_mode_ready() -> bool:
    """Whether the journal mode has already been set on this database.

    Attempting it once per process is enough: it is persistent state, so every
    later connection can skip the attempt entirely.
    """
    return False


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
            try:
                # These are per-connection and safe to set every time.
                cursor.execute("PRAGMA foreign_keys=ON")
                # Wait for a competing writer instead of failing immediately:
                # `uvicorn --reload` and any second process share this file.
                cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_busy_timeout_ms}")

                # journal_mode is a property of the *database*, not the connection,
                # and changing it needs an exclusive lock. If another process holds
                # the file (a running server, a stale -wal) this fails, and retrying
                # with a different mode would fail the same way. So: try once, and
                # carry on in whatever mode the database is already using.
                if not _journal_mode_ready():
                    try:
                        cursor.execute(f"PRAGMA journal_mode={settings.sqlite_journal_mode}")
                        _journal_mode_ready.cache_clear()
                        logger.info("SQLite journal_mode=%s", settings.sqlite_journal_mode)
                    except sqlite3.OperationalError as exc:
                        logger.warning(
                            "Could not set SQLite journal_mode=%s (%s); continuing in the "
                            "existing mode. Stop other processes using the database to change it.",
                            settings.sqlite_journal_mode,
                            exc,
                        )
                        _journal_mode_ready.cache_clear()
            finally:
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
    """Testing hook — rebind to an in-memory database.

    `StaticPool` is required: without it SQLAlchemy opens one connection per
    thread for in-memory SQLite, and TestClient runs the app on a different
    thread than the test, so the two would see separate databases.
    """
    global engine, SessionLocal
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(bind=engine)


def database_file() -> Path:
    return get_settings().database_path
