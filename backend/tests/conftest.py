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
def override_db() -> Iterator[None]:
    """Make HTTP requests use the in-memory database."""

    def override_get_db() -> Iterator[Session]:
        session = db_session.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[db_session.get_db] = override_get_db
    yield
    app.dependency_overrides.pop(db_session.get_db, None)


@pytest.fixture
def client(override_db: None) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(db: Session):
    """Create an account and return `(user, headers)` with a valid bearer token."""
    import uuid

    from app.config import get_settings
    from app.db import repositories as repo
    from app.services.auth import create_token, hash_password

    def _make(
        email: str = "walker@example.com", display_name: str = "Walker", password="outdoors123"
    ):
        user = repo.create_user(
            db,
            user_id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
        )
        token = create_token(user.id, get_settings().secret_key)
        return user, {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def user_and_headers(make_user):
    return make_user()
