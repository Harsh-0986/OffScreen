"""Schemas for discoveries, journal, and profile."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Discovery(BaseModel):
    id: str
    challenge_id: str
    image_url: str
    title: str
    description: str = ""
    score: int
    confidence: float
    category: str
    completed: bool = True
    feedback: str = ""
    reasoning: str = ""
    interesting_detail: str = ""
    visual_description: str = ""
    points_awarded: int = 0
    tagline: str = ""
    created_at: str


class DiscoveryResponse(BaseModel):
    """The shape the result screen consumes (SPEC §19)."""

    discovery: Discovery
    profile: dict | None = None


class JournalResponse(BaseModel):
    discoveries: list[Discovery]
    total: int


class ProfileResponse(BaseModel):
    id: str
    display_name: str
    total_points: int
    discoveries_count: int
    current_streak: int
    completed_challenges: int = 0
    outdoor_minutes_estimate: int = 0
    favorite_categories: dict[str, float] = Field(default_factory=dict)


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
