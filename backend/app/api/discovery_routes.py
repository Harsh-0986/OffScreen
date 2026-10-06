"""Discovery submission, journal, and profile endpoints (SPEC §19)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import read_capped_upload, resolve_user_id
from app.config import get_settings
from app.db import repositories as repo
from app.db.session import get_db
from app.errors import GemmaError, NotFoundError
from app.graph.graph import run_discovery_graph
from app.schemas.discovery import (
    Discovery,
    DiscoveryResponse,
    JournalResponse,
    ProfileResponse,
    ProfileUpdate,
)
from app.services.gemma import GemmaService, get_gemma_service
from app.services.images import store_image, validate_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["discoveries"])

UserId = Annotated[str, Depends(resolve_user_id)]
Db = Annotated[Session, Depends(get_db)]


def get_service() -> GemmaService:
    return get_gemma_service()


@router.post("/discoveries", response_model=DiscoveryResponse)
async def submit_discovery(
    image: Annotated[UploadFile, File()],
    challenge_id: Annotated[str, Form()],
    user_id: UserId,
    db: Db,
    service: Annotated[GemmaService, Depends(get_service)] = None,  # type: ignore[assignment]
) -> DiscoveryResponse:
    """Validate, save, then run the discovery graph over the photograph."""
    settings = get_settings()

    data = await read_capped_upload(image, settings.max_image_bytes)
    processed = validate_upload(
        data, declared_mime=image.content_type, max_bytes=settings.max_image_bytes
    )

    challenge = repo.get_challenge(db, user_id, challenge_id)
    if challenge is None:
        raise NotFoundError("That challenge could not be found.")

    # Save the photograph before the model runs, so a model failure never loses
    # the user's photo (SPEC §26 fallback).
    stored_name = store_image(processed.data, settings.upload_path)

    state = await run_discovery_graph(
        user_id,
        challenge_id=challenge.id,
        image_bytes=processed.data,
        image_mime_type=processed.mime_type,
        image_path=f"uploads/{stored_name}",
        service=service,
        load_challenge=_load_challenge(db),
        save_discovery=_save_discovery(db),
        refresh_profile=lambda uid: repo.get_user_profile(db, uid),
    )

    if state.get("error") and not state.get("discovery"):
        raise GemmaError(state["error"])

    return DiscoveryResponse(
        discovery=_to_schema(state["discovery"]),
        profile=state.get("user_profile"),
    )


@router.get("/journal", response_model=JournalResponse)
async def journal(
    user_id: UserId,
    db: Db,
    limit: int = 50,
    offset: int = 0,
) -> JournalResponse:
    rows = repo.list_discoveries(db, user_id, limit=min(limit, 100), offset=offset)
    return JournalResponse(discoveries=[_to_schema(r) for r in rows], total=len(rows))


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(user_id: UserId, db: Db, body: ProfileUpdate) -> ProfileResponse:
    """Set the display name.

    The MVP has no accounts (SPEC §3); this only lets someone put a name on the
    profile they already have.
    """
    repo.get_or_create_user(db, user_id)
    repo.set_display_name(db, user_id, body.display_name)
    return ProfileResponse(**repo.get_user_profile(db, user_id))


@router.get("/profile", response_model=ProfileResponse)
async def profile(user_id: UserId, db: Db) -> ProfileResponse:
    repo.get_or_create_user(db, user_id)
    return ProfileResponse(**repo.get_user_profile(db, user_id))


# ------------------------------------------------------------------ helpers


def _load_challenge(db: Session):
    def load(user_id: str, challenge_id: str) -> dict[str, Any] | None:
        row = repo.get_challenge(db, user_id, challenge_id)
        if row is None:
            return None
        return {
            "id": row.id,
            "title": row.title,
            "prompt": row.prompt,
            "category": row.category,
            "difficulty": row.difficulty,
            "estimated_minutes": row.estimated_minutes,
        }

    return load


def _save_discovery(db: Session):
    def save(**record: Any) -> dict[str, Any]:
        row = repo.add_discovery(db, **record)
        payload = row.to_public_dict()
        payload["reasoning"] = row.ai_reasoning
        payload["image_url"] = f"/{row.image_path}"
        return payload

    return save


def _to_schema(row: Any) -> Discovery:
    """Accept either an ORM row or an already-serialised dict."""
    data = row.to_public_dict() if hasattr(row, "to_public_dict") else dict(row)
    data.setdefault("reasoning", data.pop("ai_reasoning", ""))
    data.setdefault("image_url", data.get("image_path", ""))
    data.setdefault("feedback", data.pop("ai_feedback", ""))
    return Discovery(**data)
