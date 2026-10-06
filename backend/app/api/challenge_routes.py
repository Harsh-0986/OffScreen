"""Challenge endpoints (SPEC §19)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import resolve_user_id
from app.errors import GemmaError
from app.graph.graph import run_challenge_graph
from app.schemas.challenge import Challenge, ChallengeResponse, GenerateChallengeRequest
from app.services.gemma import GemmaService, get_gemma_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

UserId = Annotated[str, Depends(resolve_user_id)]


def get_service() -> GemmaService:
    return get_gemma_service()


@router.post("/generate", response_model=ChallengeResponse)
async def generate_challenge(
    user_id: UserId,
    body: GenerateChallengeRequest | None = None,
    service: Annotated[GemmaService, Depends(get_service)] = None,  # type: ignore[assignment]
) -> ChallengeResponse:
    """Generate today's discovery challenge via the LangGraph challenge graph."""
    state = await run_challenge_graph(user_id, service=service)

    if state.get("error"):
        raise GemmaError(state["error"])

    challenge: dict[str, Any] = state.get("current_challenge") or {}
    if not challenge:
        raise GemmaError()

    return ChallengeResponse(
        challenge=Challenge(
            title=challenge["title"],
            prompt=challenge["prompt"],
            category=challenge["category"],
            difficulty=challenge["difficulty"],
            estimated_minutes=challenge["estimated_minutes"],
        ),
        personalization_note=challenge.get("personalization_note"),
    )


@router.get("/today", response_model=ChallengeResponse)
async def today(user_id: UserId) -> ChallengeResponse:
    """Placeholder until Phase 5 persists challenges.

    Same behaviour as `/generate` for now: the challenge is not yet stored, so
    there is nothing to reuse.
    """
    state = await run_challenge_graph(user_id)
    if state.get("error"):
        raise GemmaError(state["error"])
    challenge: dict[str, Any] = state.get("current_challenge") or {}
    return ChallengeResponse(
        challenge=Challenge(**{k: challenge[k] for k in Challenge.model_fields if k in challenge}),
        personalization_note=challenge.get("personalization_note"),
    )
