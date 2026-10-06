"""Shared API dependencies."""

from __future__ import annotations

import uuid

from fastapi import Header, UploadFile

from app.errors import ImageValidationError, InvalidIdentityError

USER_ID_HEADER = "X-User-Id"


def resolve_user_id(x_user_id: str | None = Header(default=None)) -> str:
    """Resolve the caller's identity.

    The MVP has no authentication (SPEC §3), but the data model is multi-user.
    The frontend generates a UUID once and sends it on every request, which gives
    per-browser separation without an account system. Adding real auth later
    means replacing this function, nothing else.

    A missing header gets a fresh UUID, so a plain `curl` still works.
    """
    if not x_user_id:
        return str(uuid.uuid4())

    try:
        return str(uuid.UUID(x_user_id))
    except ValueError as exc:
        raise InvalidIdentityError(f"{USER_ID_HEADER} must be a UUID.") from exc


# Upload reads happen in chunks so an oversized body is rejected without ever
# being buffered whole.
CHUNK_SIZE = 64 * 1024


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
