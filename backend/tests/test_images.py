"""Tests for image validation, resizing, and storage (SPEC §27, §42).

Images are built in memory with Pillow so the suite needs no binary fixtures.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.errors import ImageValidationError
from app.services.images import (
    MAX_DIMENSION,
    MIN_DIMENSION,
    sniff_mime,
    store_image,
    validate_upload,
)

MAX = 10 * 1024 * 1024


def make_image(
    size: tuple[int, int] = (64, 64),
    fmt: str = "JPEG",
    color: str = "green",
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


# ---------------------------------------------------------------- sniffing


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (make_image(fmt="JPEG"), "image/jpeg"),
        (make_image(fmt="PNG"), "image/png"),
        (make_image(fmt="WEBP"), "image/webp"),
    ],
)
def test_sniffs_real_types(data: bytes, expected: str) -> None:
    assert sniff_mime(data) == expected


def test_sniff_rejects_non_images() -> None:
    assert sniff_mime(b"GIF89a") is None
    assert sniff_mime(b"%PDF-1.4") is None
    assert sniff_mime(b"") is None


# --------------------------------------------------------------- validation


def test_accepts_a_normal_photo() -> None:
    result = validate_upload(make_image(), declared_mime="image/jpeg", max_bytes=MAX)
    assert result.mime_type == "image/jpeg"
    assert result.width == 64
    assert result.original_bytes > 0


def test_rejects_empty_upload() -> None:
    with pytest.raises(ImageValidationError, match="empty"):
        validate_upload(b"", declared_mime="image/jpeg", max_bytes=MAX)


def test_rejects_oversized_upload() -> None:
    with pytest.raises(ImageValidationError, match="too large"):
        validate_upload(make_image(), declared_mime="image/jpeg", max_bytes=10)


def test_rejects_disallowed_mime_even_if_bytes_look_fine() -> None:
    """A lying content-type is refused before we decode anything."""
    with pytest.raises(ImageValidationError, match="JPEG, PNG"):
        validate_upload(make_image(), declared_mime="application/pdf", max_bytes=MAX)


def test_rejects_spoofed_extension() -> None:
    """A .exe renamed to .jpg is caught by the magic-byte check."""
    with pytest.raises(ImageValidationError, match="isn't a JPEG"):
        validate_upload(b"MZ\x90\x00" + b"\x00" * 200, declared_mime="image/jpeg", max_bytes=MAX)


def test_rejects_corrupt_image_data() -> None:
    truncated = make_image()[:40]
    with pytest.raises(ImageValidationError):
        validate_upload(truncated, declared_mime="image/jpeg", max_bytes=MAX)


def test_rejects_tiny_images() -> None:
    with pytest.raises(ImageValidationError, match="too small"):
        validate_upload(make_image((8, 8)), declared_mime="image/jpeg", max_bytes=MAX)


def test_error_messages_never_leak_internals() -> None:
    with pytest.raises(ImageValidationError) as exc:
        validate_upload(b"nope", declared_mime="image/jpeg", max_bytes=MAX)
    assert "Traceback" not in exc.value.message
    assert "b'nope'" not in exc.value.message


# ----------------------------------------------------------------- resizing


def test_large_photos_are_downscaled() -> None:
    result = validate_upload(make_image((4000, 3000)), declared_mime="image/jpeg", max_bytes=MAX)
    assert max(result.width, result.height) == MAX_DIMENSION
    assert result.was_resized is True
    assert len(result.data) < 4000 * 3000


def test_small_photos_are_left_alone() -> None:
    result = validate_upload(make_image((100, 80)), declared_mime="image/jpeg", max_bytes=MAX)
    assert (result.width, result.height) == (100, 80)
    assert result.was_resized is False


def test_resize_preserves_aspect_ratio() -> None:
    result = validate_upload(make_image((2000, 1000)), declared_mime="image/jpeg", max_bytes=MAX)
    assert result.width / result.height == pytest.approx(2.0, abs=0.05)


def test_minimum_dimension_is_enforced_after_resize() -> None:
    tall = validate_upload(make_image((2000, 40)), declared_mime="image/jpeg", max_bytes=MAX)
    assert tall.height >= MIN_DIMENSION


def test_png_with_alpha_is_flattened() -> None:
    buffer = io.BytesIO()
    Image.new("RGBA", (64, 64), (255, 0, 0, 0)).save(buffer, format="PNG")
    result = validate_upload(buffer.getvalue(), declared_mime="image/png", max_bytes=MAX)
    assert result.mime_type == "image/jpeg"
    decoded = Image.open(io.BytesIO(result.data))
    assert decoded.mode == "RGB"


# ------------------------------------------------------------------ storage


def test_store_image_uses_a_generated_name(tmp_path) -> None:
    name = store_image(b"payload", tmp_path)
    assert name.endswith(".jpg")
    assert (tmp_path / name).read_bytes() == b"payload"


def test_stored_names_do_not_contain_client_input(tmp_path) -> None:
    """No part of the client's filename reaches disk (SPEC §42)."""
    name = store_image(b"payload", tmp_path / "nested")
    assert "/" not in name
    assert ".." not in name


def test_stored_names_are_unique(tmp_path) -> None:
    names = {store_image(b"x", tmp_path) for _ in range(25)}
    assert len(names) == 25
