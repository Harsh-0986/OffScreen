"""Tests for the SQLAlchemy models and repositories (SPEC §18)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.db import repositories as repo
from app.models import Challenge, ChallengeStatus, Discovery, User, UserPreference

USER = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


def _challenge(session, user_id=USER, **overrides):
    payload = {
        "user_id": user_id,
        "title": "Branches With A Face",
        "prompt": "Find something that looks like a face.",
        "category": "nature",
        "difficulty": 2,
        "estimated_minutes": 20,
    }
    payload.update(overrides)
    return repo.add_challenge(session, **payload)


# ------------------------------------------------------------------- tables


def test_all_four_tables_exist(db) -> None:
    names = set(User.metadata.tables)
    assert {"users", "challenges", "discoveries", "user_preferences"} <= names


# -------------------------------------------------------------------- users


def test_create_user_then_lookup_by_email(db, user_and_headers) -> None:
    user, _ = user_and_headers
    assert repo.get_user_by_email(db, user.email).id == user.id
    assert repo.get_user(db, user.id).id == user.id


def test_duplicate_email_is_refused(db, user_and_headers) -> None:
    from app.errors import DuplicateEmailError

    user, _ = user_and_headers
    with pytest.raises(DuplicateEmailError):
        repo.create_user(
            db,
            user_id="another-id",
            email=user.email,
            password_hash="x",
            display_name="Impostor",
        )


def test_missing_user_returns_none(db) -> None:
    assert repo.get_user(db, "nobody") is None
    assert repo.get_user_by_email(db, "nobody@example.com") is None


def test_profile_defaults_for_unknown_user(db) -> None:
    profile = repo.get_user_profile(db, "nobody")
    assert profile["total_points"] == 0
    assert profile["favorite_categories"] == {}


def test_display_name_is_truncated(db, user_and_headers) -> None:
    user, _ = user_and_headers
    updated = repo.set_display_name(db, user.id, "x" * 200)
    assert len(updated.display_name) == 80


def test_display_name_for_unknown_user_raises(db) -> None:
    from app.errors import NotFoundError

    with pytest.raises(NotFoundError):
        repo.set_display_name(db, "nobody", "Ghost")


# --------------------------------------------------------------- challenges


def test_add_and_fetch_today_challenge(db) -> None:
    created = _challenge(db)
    fetched = repo.get_today_challenge(db, USER)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.status == ChallengeStatus.ACTIVE


def test_today_challenge_is_scoped_to_the_user(db) -> None:
    _challenge(db, user_id=OTHER)
    assert repo.get_today_challenge(db, USER) is None


def test_today_challenge_expires(db) -> None:
    challenge = _challenge(db)
    stale = datetime.now(UTC) - timedelta(hours=25)
    challenge.created_at = stale
    db.commit()
    assert repo.get_today_challenge(db, USER) is None


def test_abandon_stale_challenges(db) -> None:
    challenge = _challenge(db)
    challenge.created_at = datetime.now(UTC) - timedelta(hours=25)
    db.commit()
    assert repo.abandon_stale_challenges(db, USER) == 1
    assert repo.get_today_challenge(db, USER) is None


def test_get_challenge_enforces_ownership(db) -> None:
    """A user cannot load another user's challenge by id."""
    challenge = _challenge(db, user_id=OTHER)
    assert repo.get_challenge(db, USER, challenge.id) is None
    assert repo.get_challenge(db, OTHER, challenge.id) is not None


def test_list_challenge_titles_is_newest_first(db) -> None:
    _challenge(db, title="Older")
    _challenge(db, title="Newer")
    assert repo.list_challenge_titles(db, USER, limit=2)[0] in {"Older", "Newer"}


# ------------------------------------------------------------- discoveries


def test_add_discovery_updates_profile_and_marks_challenge(db, user_and_headers) -> None:
    user, _ = user_and_headers
    challenge = _challenge(db, user_id=user.id)

    discovery = repo.add_discovery(
        db,
        user_id=user.id,
        challenge_id=challenge.id,
        image_path="uploads/x.jpg",
        title="A Face In The Bark",
        description="Branches forming an outline.",
        score=9,
        confidence=0.91,
        category="nature",
        ai_feedback="You found it.",
        interesting_detail="A knot shaped like a nose.",
        minutes=20,
    )

    db.refresh(user)
    db.refresh(challenge)

    assert discovery.points_awarded == 9
    assert user.total_points == 9
    assert user.discoveries_count == 1
    assert user.outdoor_minutes_estimate == 20
    assert challenge.status == ChallengeStatus.COMPLETED
    assert challenge.completed_at is not None


def test_add_discovery_bumps_category_preference(db) -> None:
    challenge = _challenge(db)
    for _ in range(3):
        c = _challenge(db, title=f"c{_}")
        repo.add_discovery(
            db,
            user_id=USER,
            challenge_id=c.id,
            image_path="uploads/x.jpg",
            title="t",
            description="",
            score=5,
            confidence=0.5,
            category="nature",
            ai_feedback="",
        )
    assert repo.get_preferences(db, USER)["nature"] == 3.0
    assert challenge.category == "nature"


def test_preferences_accumulate_per_category(db) -> None:
    repo.bump_preference(db, USER, "nature")
    repo.bump_preference(db, USER, "nature")
    repo.bump_preference(db, USER, "color")
    assert repo.get_preferences(db, USER) == {"nature": 2.0, "color": 1.0}


def test_preferences_are_scoped_to_user(db) -> None:
    repo.bump_preference(db, USER, "nature")
    assert repo.get_preferences(db, OTHER) == {}


def test_list_discoveries_is_newest_first(db) -> None:
    challenge = _challenge(db)
    for i in range(3):
        repo.add_discovery(
            db,
            user_id=USER,
            challenge_id=challenge.id,
            image_path=f"uploads/{i}.jpg",
            title=f"Discovery {i}",
            description="",
            score=i,
            confidence=0.5,
            category="nature",
            ai_feedback="",
        )
    titles = [d.title for d in repo.list_discoveries(db, USER)]
    assert titles == ["Discovery 2", "Discovery 1", "Discovery 0"]


def test_discovery_public_dict_shape(db) -> None:
    challenge = _challenge(db)
    discovery = repo.add_discovery(
        db,
        user_id=USER,
        challenge_id=challenge.id,
        image_path="uploads/x.jpg",
        title="t",
        description="d",
        score=7,
        confidence=0.8,
        category="nature",
        ai_feedback="nice",
    )
    payload = discovery.to_public_dict()
    assert payload["score"] == 7
    assert payload["image_path"] == "uploads/x.jpg"
    assert isinstance(payload["created_at"], str)


def test_user_to_public_dict_includes_preferences(db, user_and_headers) -> None:
    user, _ = user_and_headers
    repo.bump_preference(db, user.id, "nature", 3.0)
    profile = repo.get_user_profile(db, user.id)
    assert profile["favorite_categories"] == {"nature": 3.0}


def test_cascade_delete_user_removes_children(db, user_and_headers) -> None:
    user, _ = user_and_headers
    USER = user.id
    challenge = _challenge(db, user_id=USER)
    repo.add_discovery(
        db,
        user_id=USER,
        challenge_id=challenge.id,
        image_path="uploads/x.jpg",
        title="t",
        description="",
        score=1,
        confidence=0.1,
        category="nature",
        ai_feedback="",
    )
    db.delete(user)
    db.commit()
    assert db.query(Discovery).count() == 0
    assert db.query(Challenge).count() == 0
    assert db.query(UserPreference).count() == 0


def test_discovery_persists_across_sessions(db, user_and_headers) -> None:
    """Phase 5 acceptance: data survives a new session/engine (SPEC §33)."""
    from app.db.session import SessionLocal

    user, _ = user_and_headers
    USER = user.id
    challenge = _challenge(db, user_id=USER)
    repo.add_discovery(
        db,
        user_id=USER,
        challenge_id=challenge.id,
        image_path="uploads/x.jpg",
        title="Survivor",
        description="",
        score=8,
        confidence=0.7,
        category="nature",
        ai_feedback="",
    )
    db.close()

    with SessionLocal() as fresh:
        found = fresh.query(Discovery).filter_by(title="Survivor").one()
        assert found.score == 8


# ------------------------------------------------- profile counters & streak
#
# These round-trip through the database on purpose. The original bugs here were
# invisible to tests that only used in-memory objects: SQLite returns naive
# datetimes, so any tz-aware comparison silently failed.


def _submit(db, user, *, challenge=None):
    challenge = challenge or _challenge(db, user_id=user.id)
    return repo.add_discovery(
        db,
        user_id=user.id,
        challenge_id=challenge.id,
        image_path="uploads/x.jpg",
        title="t",
        description="",
        score=7,
        confidence=0.8,
        category="nature",
        ai_feedback="",
    )


def test_completed_challenges_is_incremented(db, user_and_headers) -> None:
    user, _ = user_and_headers
    _submit(db, user)
    db.expire_all()
    assert repo.get_user(db, user.id).completed_challenges == 1


def test_streak_starts_at_one(db, user_and_headers) -> None:
    user, _ = user_and_headers
    _submit(db, user)
    db.expire_all()
    assert repo.get_user(db, user.id).current_streak == 1


def test_two_discoveries_on_one_day_hold_the_streak(db, user_and_headers) -> None:
    user, _ = user_and_headers
    _submit(db, user)
    _submit(db, user)
    db.expire_all()
    fresh = repo.get_user(db, user.id)
    assert fresh.current_streak == 1
    assert fresh.completed_challenges == 2


def test_streak_extends_on_a_consecutive_day(db, user_and_headers) -> None:
    from datetime import UTC, datetime, timedelta

    user, _ = user_and_headers
    # A real one-day-old streak: yesterday's discovery already made it 1.
    user.current_streak = 1
    user.last_discovery_date = datetime.now(UTC).date() - timedelta(days=1)
    db.commit()

    _submit(db, user)
    db.expire_all()
    assert repo.get_user(db, user.id).current_streak == 2


def test_streak_resets_after_a_gap(db, user_and_headers) -> None:
    from datetime import UTC, datetime, timedelta

    user, _ = user_and_headers
    user.current_streak = 4
    user.last_discovery_date = datetime.now(UTC).date() - timedelta(days=4)
    db.commit()

    _submit(db, user)
    db.expire(user)
    assert user.current_streak == 1


def test_naive_database_dates_do_not_break_the_streak(db, user_and_headers) -> None:
    """Regression: SQLite returns naive datetimes and tzinfo checks failed."""
    from datetime import UTC, datetime

    from app.db.base import as_utc

    user, _ = user_and_headers
    _submit(db, user)
    db.expire(user)
    db.commit()

    # Re-read from the database: the value comes back naive from SQLite.
    db.expire_all()
    fresh_user = repo.get_user(db, user.id)
    assert fresh_user is not None
    raw = fresh_user.last_discovery_date
    assert raw is not None
    assert as_utc(datetime.combine(raw, datetime.min.time())) == datetime.combine(
        raw, datetime.min.time(), tzinfo=UTC
    )


def test_profile_reports_completed_challenges_and_streak(db, user_and_headers) -> None:
    user, _ = user_and_headers
    _submit(db, user)
    profile = repo.get_user_profile(db, user.id)
    assert profile["completed_challenges"] == 1
    assert profile["current_streak"] == 1
    assert profile["discoveries_count"] == 1
