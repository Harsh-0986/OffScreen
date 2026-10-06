"""Image validation, sanitisation, and resizing (SPEC §27, §42).

The uploaded file is treated as hostile:

- the type is confirmed by magic bytes, not by the client-supplied content type
- the size is capped while streaming, so a huge body is never fully buffered
- the stored filename is a generated UUID, so the original name is never trusted
- oversized images are downscaled before being sent to the model
"""

from __future__ import annotations

import io
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.errors import ImageValidationError

logger = logging.getLogger(__name__)

# Magic-byte signatures for the formats we accept.
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),
)

SUPPORTED_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")

# Longest edge sent to the model. Phone photos are far larger than a vision
# model needs, and resizing cuts latency and token cost (SPEC §43).
MAX_DIMENSION = 1280

MIN_DIMENSION = 32


@dataclass
class ProcessedImage:
    """A validated, model-ready image."""

    data: bytes
    mime_type: str
    width: int
    height: int
    original_bytes: int
    resized: bool = False
    stored_name: str | None = None

    @property
    def was_resized(self) -> bool:
        return self.resized


def sniff_mime(data: bytes) -> str | None:
    """Detect the real image type from its leading bytes."""
    for signature, mime in _MAGIC:
        if data.startswith(signature):
            return mime
    return None


def validate_upload(
    data: bytes,
    *,
    declared_mime: str | None,
    max_bytes: int,
) -> ProcessedImage:
    """Validate raw bytes and return a resized, model-ready image.

    Raises `ImageValidationError` with a user-safe message on any failure.
    """
    if not data:
        raise ImageValidationError("That file was empty. Try taking the photo again.")

    if len(data) > max_bytes:
        raise ImageValidationError(
            f"That photo is too large. Keep it under {max_bytes // (1024 * 1024)} MB."
        )

    actual = sniff_mime(data)
    if actual is None:
        raise ImageValidationError("That file isn't a JPEG, PNG, or WebP image.")

    if declared_mime and declared_mime.lower() not in SUPPORTED_MIME_TYPES:
        raise ImageValidationError("Only JPEG, PNG, and WebP photos are supported.")

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.info("Rejected undecodable image: %s", exc)
        raise ImageValidationError("That image could not be read. Try a different photo.") from exc

    if image.width < MIN_DIMENSION or image.height < MIN_DIMENSION:
        raise ImageValidationError("That image is too small to judge.")

    image = _to_rgb(image)
    resized = _resize(image)
    buffer = io.BytesIO()
    resized.save(buffer, format="JPEG", quality=88, optimize=True)

    return ProcessedImage(
        data=buffer.getvalue(),
        mime_type="image/jpeg",
        width=resized.width,
        height=resized.height,
        original_bytes=len(data),
        resized=resized is not image,
    )


def store_image(data: bytes, upload_dir: Path, suffix: str = ".jpg") -> str:
    """Write bytes to disk under a generated UUID filename.

    The client's filename is deliberately discarded (SPEC §42).
    """
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4()}{suffix}"
    path = upload_dir / name
    path.write_bytes(data)
    return name


def _to_rgb(image: Image.Image) -> Image.Image:
    """Flatten transparency onto white so WebP/PNG alpha does not confuse the model."""
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        return background
    return image.convert("RGB")


def _resize(image: Image.Image) -> Image.Image:
    longest = max(image.size)
    if longest <= MAX_DIMENSION:
        return image
    scale = MAX_DIMENSION / longest
    size = (
        max(MIN_DIMENSION, round(image.width * scale)),
        max(MIN_DIMENSION, round(image.height * scale)),
    )
    return image.resize(size, Image.Resampling.LANCZOS)
