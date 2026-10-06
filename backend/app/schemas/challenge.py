"""HTTP-facing schemas for challenges."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Challenge(BaseModel):
    """A challenge as returned to the client."""

    id: str | None = None
    title: str
    prompt: str
    category: str
    difficulty: int = Field(ge=1, le=4)
    estimated_minutes: int = Field(ge=1, le=600)


class ChallengeResponse(BaseModel):
    challenge: Challenge
    personalization_note: str | None = None


class GenerateChallengeRequest(BaseModel):
    """Optional body for POST /api/challenges/generate.

    Phase 5 reuses an existing unexpired challenge instead of generating a new one.
    """

    force_new: bool = False
