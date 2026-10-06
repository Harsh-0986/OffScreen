"""Shared API dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, UploadFile
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import repositories as repo
from app.db.session import get_db
from app.errors import AuthError, ImageValidationError
from app.models import User
from app.services.auth import decode_token

# Upload reads happen in chunks so an oversized body is rejected without ever
# being buffered whole.
CHUNK_SIZE = 64 * 1024


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> User:
    """Resolve the signed-in user from a bearer token.

    There is no anonymous access: every discovery belongs to an account.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Please sign in to continue.")

    payload = decode_token(authorization.split(" ", 1)[1].strip(), settings.secret_key)
    user = repo.get_user(db, payload.user_id)
    if user is None:
        raise AuthError("That account no longer exists.")
    return user


async def read_capped_upload(upload: UploadFile, max_bytes: int) -> bytes:
    """Read an upload, aborting as soon as the size cap is exceeded."""
    buffer = bytearray()
    while chunk := await upload.read(CHUNK_SIZE):
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise ImageValidationError(
                f"That photo is too large. Keep it under {max_bytes // (1024 * 1024)} MB."
            )
    return bytes(buffer)
