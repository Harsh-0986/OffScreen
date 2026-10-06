"""Pydantic schemas exposed by the API and used to validate model output."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str


class GemmaTestResponse(BaseModel):
    success: bool
    model: str | None = None
    sample: str | None = None
    structured_ok: bool | None = None


# ------------------------------------------------------------- model schemas


class ChallengeDraft(BaseModel):
    """Raw model output for challenge generation (SPEC §10)."""

    title: str = Field(min_length=1, max_length=80)
    prompt: str = Field(min_length=1, max_length=400)
    category: str = Field(min_length=1, max_length=40)
    difficulty: int = Field(ge=1, le=4)
    estimated_minutes: int = Field(ge=5, le=120)

    @field_validator("category")
    @classmethod
    def known_category(cls, value: str) -> str:
        from app.constants import CHALLENGE_CATEGORIES

        normalized = value.strip().lower()
        if normalized not in CHALLENGE_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(CHALLENGE_CATEGORIES)}")
        return normalized


class PhotoAnalysis(BaseModel):
    """Raw model output for the photo analysis node (SPEC §12)."""

    visual_description: str
    subjects: list[str] = Field(default_factory=list, max_length=8)
    setting: str = ""
    unexpected_details: list[str] = Field(default_factory=list, max_length=5)
    image_quality: str = "clear"
    description_caveat: str = ""


class DiscoveryEvaluation(BaseModel):
    """Raw model output for the evaluation node (SPEC §13)."""

    completed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    what_was_found: str
    visual_description: str = ""
    reasoning_summary: str = ""
    interesting_detail: str = ""
    score: int = Field(ge=0, le=10)
    feedback: str = ""

    @field_validator("score")
    @classmethod
    def score_in_range(cls, value: int) -> int:
        if not 0 <= value <= 10:
            raise ValueError("score must be between 0 and 10")
        return value


class DiscoveryFeedback(BaseModel):
    """Raw model output for the reflection node (SPEC §5)."""

    title: str = Field(min_length=1, max_length=80)
    reflection: str = Field(min_length=1, max_length=400)
    tagline: str = Field(default="", max_length=80)
