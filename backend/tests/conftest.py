"""Shared pytest fixtures.

Every test runs against a fresh in-memory SQLite database, so the suite never
touches the developer's `outside.db`.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import session as db_session
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database() -> Iterator[None]:
    db_session.reset_engine_for_tests()
    yield


@pytest.fixture
def db() -> Iterator[Session]:
    session = db_session.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """TestClient whose requests use the in-memory database."""

    def override_get_db() -> Iterator[Session]:
        session = db_session.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[db_session.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(db_session.get_db, None)
