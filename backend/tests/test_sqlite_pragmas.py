"""SQLite connection setup: pragmas must never be able to take the app down.

`PRAGMA journal_mode` is database state that needs an exclusive lock, so it fails
whenever another process holds the file — e.g. a running `uvicorn --reload`, or a
stale `-wal`/`-shm` pair. A failure there must be survivable.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.db import session as db_session


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point settings at a throwaway database and rebuild the engine."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    db_session.get_settings.cache_clear()
    engine = db_session._build_engine()
    yield engine
    engine.dispose()


def test_pragmas_are_applied(temp_db) -> None:
    db_session.init_db()
    with temp_db.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar() > 0


def test_two_connections_coexist(temp_db) -> None:
    """Two connections are normal with --reload; neither may error on connect."""
    db_session.init_db()
    with temp_db.connect() as first:
        first.exec_driver_sql("CREATE TABLE IF NOT EXISTS t (id INTEGER)")
        first.commit()

    with temp_db.connect() as second:
        second.exec_driver_sql("INSERT INTO t (id) VALUES (1)")
        second.commit()

    with temp_db.connect() as third:
        assert third.exec_driver_sql("SELECT count(*) FROM t").scalar() == 1


def test_locked_database_does_not_break_connecting(
    temp_db, monkeypatch, caplog
) -> None:
    """A second process holding an exclusive lock must not stop us connecting."""
    db_session.init_db()

    # Hold an exclusive lock on the database for the duration of the attempt.
    blocker = sqlite3.connect(temp_db.url.database, isolation_level=None)
    blocker.execute("BEGIN EXCLUSIVE")

    db_session._journal_mode_ready.cache_clear()
    try:
        with caplog.at_level("WARNING"):
            engine = db_session._build_engine()  # must not raise
            with engine.connect() as connection:
                assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar() > 0
    finally:
        blocker.rollback()
        blocker.close()
        engine.dispose()

    assert any("journal_mode" in record.message for record in caplog.records)


def test_repeated_connects_are_stable(temp_db) -> None:
    """journal_mode is persistent state, so later connections simply reuse it."""
    db_session.init_db()
    modes = []
    for _ in range(5):
        with temp_db.connect() as connection:
            modes.append(connection.exec_driver_sql("PRAGMA journal_mode").scalar())

    assert len(set(modes)) == 1, f"journal mode flickered between connections: {modes}"
