"""Photo upload + analysis endpoint (SPEC §31)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import read_capped_upload, resolve_user_id
from app.config import get_settings
from app.db import repositories as repo
from app.db.session import get_db
from app.schemas.photo import PhotoAnalysisResponse
from app.services.analysis import analyze_photo
from app.services.gemma import GemmaService, get_gemma_service
from app.services.images import store_image, validate_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/photos", tags=["photos"])


def get_service() -> GemmaService:
    return get_gemma_service()


@router.post("/analyze", response_model=PhotoAnalysisResponse)
async def analyze(
    image: Annotated[UploadFile, File(description="JPEG, PNG or WebP photograph")],
    challenge_id: Annotated[str | None, Form()] = None,
    save: Annotated[bool, Form()] = False,
    user_id: Annotated[str, Depends(resolve_user_id)] = "",
    db=Depends(get_db),
    service: Annotated[GemmaService, Depends(get_service)] = None,  # type: ignore[assignment]
) -> PhotoAnalysisResponse:
    """Validate the upload, then describe what is visible. No scoring yet."""
    settings = get_settings()

    data = await read_capped_upload(image, settings.max_image_bytes)
    processed = validate_upload(
        data, declared_mime=image.content_type, max_bytes=settings.max_image_bytes
    )

    challenge = None
    if challenge_id:
        row = repo.get_challenge(db, user_id, challenge_id)
        if row is not None:
            challenge = {"id": row.id, "title": row.title, "prompt": row.prompt}

    if save:
        processed.stored_name = store_image(processed.data, settings.upload_path)

    analysis = analyze_photo(
        service,
        image_bytes=processed.data,
        mime_type=processed.mime_type,
        challenge=challenge,
    )

    return PhotoAnalysisResponse(
        **analysis.model_dump(),
        width=processed.width,
        height=processed.height,
        original_bytes=processed.original_bytes,
        resized=processed.was_resized,
    )
