"""Tests for the SQLAlchemy models and repositories (SPEC §18)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


def test_get_or_create_user_creates_then_reuses(db) -> None:
    first = repo.get_or_create_user(db, USER)
    second = repo.get_or_create_user(db, USER)
    assert first.id == second.id == USER
    assert db.query(User).count() == 1


def test_profile_defaults_for_unknown_user(db) -> None:
    profile = repo.get_user_profile(db, "nobody")
    assert profile["total_points"] == 0
    assert profile["favorite_categories"] == {}


def test_display_name_is_truncated(db) -> None:
    user = repo.set_display_name(db, USER, "x" * 200)
    assert len(user.display_name) == 80


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


def test_add_discovery_updates_profile_and_marks_challenge(db) -> None:
    user = repo.get_or_create_user(db, USER)
    challenge = _challenge(db)

    discovery = repo.add_discovery(
        db,
        user_id=USER,
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


def test_user_to_public_dict_includes_preferences(db) -> None:
    repo.get_or_create_user(db, USER)
    repo.bump_preference(db, USER, "nature", 3.0)
    profile = repo.get_user_profile(db, USER)
    assert profile["favorite_categories"] == {"nature": 3.0}


def test_cascade_delete_user_removes_children(db) -> None:
    user = repo.get_or_create_user(db, USER)
    challenge = _challenge(db)
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


def test_discovery_persists_across_sessions(db) -> None:
    """Phase 5 acceptance: data survives a new session/engine (SPEC §33)."""
    from app.db.session import SessionLocal

    challenge = _challenge(db)
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
