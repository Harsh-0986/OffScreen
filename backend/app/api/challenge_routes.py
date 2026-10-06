"""Challenge endpoints (SPEC §19)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import repositories as repo
from app.db.session import get_db
from app.errors import GemmaError
from app.graph.graph import run_challenge_graph
from app.models import User
from app.schemas.challenge import Challenge, ChallengeResponse, GenerateChallengeRequest
from app.services.gemma import GemmaService, get_gemma_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

UserId = Annotated[User, Depends(get_current_user)]
Db = Annotated[Session, Depends(get_db)]


def get_service() -> GemmaService:
    return get_gemma_service()


@router.post("/generate", response_model=ChallengeResponse)
async def generate_challenge(
    user: UserId,
    db: Db,
    body: GenerateChallengeRequest | None = None,
    service: Annotated[GemmaService, Depends(get_service)] = None,  # type: ignore[assignment]
) -> ChallengeResponse:
    """Return today's challenge, generating and persisting one if needed.

    Within the TTL the stored challenge is reused, so refreshing the page does
    not burn a new challenge (SPEC §20 shows a single challenge per day).
    """
    if not (body and body.force_new):
        existing = repo.get_today_challenge(db, user.id)
        if existing is not None:
            return _to_response(existing, note="reused today's challenge")

    state = await run_challenge_graph(
        user.id,
        service=service,
        load_profile=lambda uid: repo.get_user_profile(db, uid),
        load_history=lambda uid: repo.list_challenge_titles(db, uid),
        load_discoveries=lambda uid: repo.list_discovery_summaries(db, uid),
    )

    if state.get("error"):
        raise GemmaError(state["error"])

    draft: dict[str, Any] = state.get("current_challenge") or {}
    if not draft:
        raise GemmaError()

    challenge = repo.add_challenge(
        db,
        user_id=user.id,
        title=draft["title"],
        prompt=draft["prompt"],
        category=draft["category"],
        difficulty=draft["difficulty"],
        estimated_minutes=draft["estimated_minutes"],
    )
    return _to_response(challenge, note=draft.get("personalization_note"))


@router.get("/today", response_model=ChallengeResponse)
async def today(user: UserId, db: Db) -> ChallengeResponse:
    """The user's current challenge, generated on first request of the day."""
    return await generate_challenge(user, db, None, None)


def _to_response(challenge, note: str | None = None) -> ChallengeResponse:
    return ChallengeResponse(
        challenge=Challenge(
            id=challenge.id,
            title=challenge.title,
            prompt=challenge.prompt,
            category=challenge.category,
            difficulty=challenge.difficulty,
            estimated_minutes=challenge.estimated_minutes,
        ),
        personalization_note=note,
    )
