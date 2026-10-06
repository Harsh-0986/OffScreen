"""Schemas for the photo analysis endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PhotoAnalysisResponse(BaseModel):
    """What Gemma saw. No scoring yet — that is Phase 4 (SPEC §31)."""

    visual_description: str
    subjects: list[str] = Field(default_factory=list)
    setting: str = ""
    unexpected_details: list[str] = Field(default_factory=list)
    image_quality: str = "clear"
    description_caveat: str = ""

    # Upload facts, useful for the UI and for debugging model behaviour.
    width: int = 0
    height: int = 0
    original_bytes: int = 0
    resized: bool = False
