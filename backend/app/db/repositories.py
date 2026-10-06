"""Data access functions.

Thin, explicit query helpers — no generic repository abstraction. LangGraph
nodes receive these as callables, which keeps the graph testable without a
database and keeps SQL out of the nodes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Challenge, ChallengeStatus, Discovery, User, UserPreference

# How long a generated challenge stays "today's".
CHALLENGE_TTL_HOURS = 24


# ------------------------------------------------------------------- users


def get_or_create_user(session: Session, user_id: str) -> User:
    """Return the user, creating a row on first sight.

    The MVP has no sign-up (SPEC §3), so the first request bootstraps the profile.
    """
    user = session.get(User, user_id)
    if user is not None:
        return user

    user = User(id=user_id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_profile(session: Session, user_id: str) -> dict:
    user = session.get(User, user_id)
    if user is None:
        return {
            "id": user_id,
            "display_name": "Curious human",
            "total_points": 0,
            "discoveries_count": 0,
            "current_streak": 0,
            "completed_challenges": 0,
            "outdoor_minutes_estimate": 0,
            "favorite_categories": {},
        }
    return user.to_public_dict()


def set_display_name(session: Session, user_id: str, display_name: str) -> User:
    user = get_or_create_user(session, user_id)
    user.display_name = display_name[:80]
    session.commit()
    session.refresh(user)
    return user


# -------------------------------------------------------------- challenges


def add_challenge(
    session: Session,
    *,
    user_id: str,
    title: str,
    prompt: str,
    category: str,
    difficulty: int,
    estimated_minutes: int,
) -> Challenge:
    challenge = Challenge(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        prompt=prompt,
        category=category,
        difficulty=difficulty,
        estimated_minutes=estimated_minutes,
        status=ChallengeStatus.ACTIVE,
    )
    session.add(challenge)
    session.commit()
    session.refresh(challenge)
    return challenge


def get_today_challenge(session: Session, user_id: str) -> Challenge | None:
    """The user's active challenge created within the TTL, if any."""
    cutoff = datetime.now(UTC) - timedelta(hours=CHALLENGE_TTL_HOURS)
    stmt = (
        select(Challenge)
        .where(
            Challenge.user_id == user_id,
            Challenge.status == ChallengeStatus.ACTIVE,
            Challenge.created_at >= cutoff,
        )
        .order_by(Challenge.created_at.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def get_challenge(session: Session, user_id: str, challenge_id: str) -> Challenge | None:
    stmt = select(Challenge).where(Challenge.id == challenge_id, Challenge.user_id == user_id)
    return session.scalars(stmt).first()


def list_challenge_titles(session: Session, user_id: str, limit: int = 8) -> list[str]:
    stmt = (
        select(Challenge.title)
        .where(Challenge.user_id == user_id)
        .order_by(Challenge.created_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def abandon_stale_challenges(
    session: Session, user_id: str, ttl_hours: int = CHALLENGE_TTL_HOURS
) -> int:
    """Mark expired active challenges as abandoned so 'today' returns a fresh one."""
    cutoff = datetime.now(UTC) - timedelta(hours=ttl_hours)
    stmt = select(Challenge).where(
        Challenge.user_id == user_id,
        Challenge.status == ChallengeStatus.ACTIVE,
        Challenge.created_at < cutoff,
    )
    stale = list(session.scalars(stmt))
    for challenge in stale:
        challenge.status = ChallengeStatus.ABANDONED
    if stale:
        session.commit()
    return len(stale)


# ------------------------------------------------------------- discoveries


def add_discovery(
    session: Session,
    *,
    user_id: str,
    challenge_id: str,
    image_path: str,
    title: str,
    description: str,
    score: int,
    confidence: float,
    category: str,
    ai_feedback: str,
    completed: bool = True,
    points_awarded: int | None = None,
    **extra: str,
) -> Discovery:
    """Persist a discovery and update the user's profile in the same transaction."""
    discovery = Discovery(
        id=str(uuid.uuid4()),
        challenge_id=challenge_id,
        user_id=user_id,
        image_path=image_path,
        title=title,
        description=description,
        score=score,
        confidence=confidence,
        category=category,
        completed=completed,
        ai_feedback=ai_feedback,
        points_awarded=score if points_awarded is None else points_awarded,
        ai_reasoning=extra.get("ai_reasoning", ""),
        interesting_detail=extra.get("interesting_detail", ""),
        visual_description=extra.get("visual_description", ""),
    )
    session.add(discovery)

    user = session.get(User, user_id)
    if user is not None:
        user.total_points += discovery.points_awarded
        user.discoveries_count += 1
        user.outdoor_minutes_estimate += extra.get("minutes", 0)

    # Always record the taste signal, even if the profile row is missing, so a
    # discovery never silently loses the user's category weighting.
    bump_preference(session, user_id, category)

    challenge = session.get(Challenge, challenge_id)
    if challenge is not None:
        challenge.status = ChallengeStatus.COMPLETED
        challenge.completed_at = datetime.now(UTC)
        user = user or session.get(User, user_id)
        if user is not None and _same_utc_day(challenge.created_at, datetime.now(UTC)):
            user.current_streak += 1

    session.commit()
    session.refresh(discovery)
    return discovery


def list_discoveries(
    session: Session, user_id: str, *, limit: int = 50, offset: int = 0
) -> list[Discovery]:
    stmt = (
        select(Discovery)
        .where(Discovery.user_id == user_id)
        .order_by(Discovery.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt))


def list_discovery_summaries(session: Session, user_id: str, limit: int = 8) -> list[str]:
    stmt = (
        select(Discovery.title)
        .where(Discovery.user_id == user_id)
        .order_by(Discovery.created_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


# ------------------------------------------------------------- preferences


def bump_preference(session: Session, user_id: str, category: str, amount: float = 1.0) -> None:
    """Increment the user's weight for a category (SPEC §17)."""
    stmt = select(UserPreference).where(
        UserPreference.user_id == user_id, UserPreference.category == category
    )
    preference = session.scalars(stmt).first()
    if preference is None:
        preference = UserPreference(user_id=user_id, category=category, weight=amount)
        session.add(preference)
    else:
        preference.weight += amount
    # Sessions are created with autoflush off; flush so the row is visible to
    # later queries in the same transaction.
    session.flush()


def get_preferences(session: Session, user_id: str) -> dict[str, float]:
    stmt = select(UserPreference).where(UserPreference.user_id == user_id)
    return {p.category: p.weight for p in session.scalars(stmt)}


def _same_utc_day(left: datetime, right: datetime) -> bool:
    return left.date() == right.date() and left.tzinfo is not None and right.tzinfo is not None


def today() -> date:
    return datetime.now(UTC).date()
