"""Diagnostic endpoint proving the Gemma connection works (SPEC §29)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.errors import AppError, GemmaError
from app.schemas.ai import ChallengeDraft
from app.services.gemma import GemmaService, get_gemma_service

router = APIRouter(prefix="/api/test", tags=["test"])


class GemmaTestResponse(BaseModel):
    success: bool
    model: str | None = None
    sample: str | None = None
    structured_ok: bool | None = None
    error: str | None = None


def get_service() -> GemmaService:
    """Dependency seam so tests can swap in a stub without touching the network."""
    return get_gemma_service()


@router.post("/gemma", response_model=GemmaTestResponse)
def test_gemma(service: GemmaService = Depends(get_service)) -> GemmaTestResponse:
    """Two live calls: free text, then structured JSON.

    Returns 200 with `success: false` rather than raising, so the endpoint can be
    used as a setup checklist.
    """
    try:
        sample = service.generate_text(
            "In one short sentence, what should someone do outside right now?"
        )
    except GemmaError as exc:
        return GemmaTestResponse(
            success=False, model=service.model, error=f"{exc.message} ({exc.detail or 'no detail'})"
        )

    structured_ok = False
    try:
        draft = service.generate_structured(
            "Generate a simple outdoor challenge for a first-time user.",
            ChallengeDraft,
        )
        structured_ok = bool(draft.title and draft.prompt)
    except AppError as exc:
        return GemmaTestResponse(
            success=False,
            model=service.model,
            sample=sample,
            structured_ok=False,
            error=f"text ok, structured output failed: {exc.message}",
        )

    return GemmaTestResponse(
        success=True, model=service.model, sample=sample, structured_ok=structured_ok
    )
