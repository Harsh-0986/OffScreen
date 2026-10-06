"""Tests for the photo upload + analysis endpoint (no network)."""

from __future__ import annotations

import io

from PIL import Image

from app.api.photo_routes import get_service
from app.db import repositories as repo
from app.main import app
from app.schemas.ai import PhotoAnalysis

USER = "11111111-1111-4111-8111-111111111111"


def image_bytes(size=(64, 64), fmt="JPEG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "green").save(buffer, format=fmt)
    return buffer.getvalue()


class FakeGemma:
    def __init__(self, analysis=None, error=None):
        self.analysis = analysis or PhotoAnalysis(
            visual_description="A mossy wall beside a path.",
            subjects=["moss", "wall"],
            setting="outdoors",
            unexpected_details=["a beetle"],
            image_quality="clear",
            description_caveat="",
        )
        self.error = error
        self.calls: list[tuple] = []

    def generate_structured_from_image(
        self, prompt, image_bytes, mime_type, schema, *, system=None
    ):
        self.calls.append({"prompt": prompt, "bytes": image_bytes, "mime": mime_type})
        if self.error:
            raise self.error
        return self.analysis

    def generate_structured(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("analysis must use the multimodal call")


def override(service: FakeGemma):
    app.dependency_overrides[get_service] = lambda: service


def post(client, *, data=image_bytes(), filename="photo.jpg", content_type="image/jpeg", **form):
    override_for_form = {**form}
    return client.post(
        "/api/photos/analyze",
        files={"image": (filename, data, content_type)},
        data=override_for_form,
        headers={"X-User-Id": USER},
    )


def test_returns_visual_description(client) -> None:
    gemma = FakeGemma()
    override(gemma)
    try:
        response = post(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["visual_description"] == "A mossy wall beside a path."
    assert body["subjects"] == ["moss", "wall"]
    assert "score" not in body, "Phase 3 returns no scoring yet"


def test_upload_metadata_is_returned(client) -> None:
    override(FakeGemma())
    try:
        body = post(client, data=image_bytes((4000, 3000))).json()
    finally:
        app.dependency_overrides.clear()
    assert body["width"] == 1280
    assert body["resized"] is True
    assert body["original_bytes"] > 0


def test_model_receives_the_resized_jpeg(client) -> None:
    gemma = FakeGemma()
    override(gemma)
    try:
        post(client, data=image_bytes((4000, 3000)))
    finally:
        app.dependency_overrides.clear()
    assert gemma.calls[0]["mime"] == "image/jpeg"
    assert len(gemma.calls[0]["bytes"]) < 1_000_000


def test_rejects_non_image_upload(client) -> None:
    override(FakeGemma())
    try:
        response = post(client, data=b"MZ executable", filename="virus.jpg")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "Traceback" not in response.text


def test_rejects_unsupported_content_type(client) -> None:
    override(FakeGemma())
    try:
        response = post(client, data=image_bytes(), content_type="application/pdf")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400


def test_rejects_upload_over_the_size_cap(client, monkeypatch) -> None:
    """The cap is enforced while streaming, before the model is ever called."""
    monkeypatch.setattr(
        "app.api.photo_routes.get_settings.cache_clear", lambda: None, raising=False
    )
    gemma = FakeGemma()
    override(gemma)
    try:
        response = _post_with_cap(client, max_bytes=1024)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "too large" in response.json()["detail"]
    assert gemma.calls == [], "the model must not be called for a rejected upload"


def _post_with_cap(client, *, max_bytes: int):
    """POST with a temporarily lowered MAX_IMAGE_BYTES."""
    from app.api import photo_routes

    original = photo_routes.get_settings

    class Capped:
        max_image_bytes = max_bytes
        upload_path = original().upload_path

    photo_routes.get_settings = lambda: Capped()  # type: ignore[assignment]
    try:
        return post(client, data=image_bytes((900, 900)))
    finally:
        photo_routes.get_settings = original  # type: ignore[assignment]


def test_challenge_context_is_passed_when_id_is_known(client, db) -> None:
    challenge = repo.add_challenge(
        db,
        user_id=USER,
        title="A Face",
        prompt="Find something that looks like a face.",
        category="nature",
        difficulty=2,
        estimated_minutes=20,
    )
    gemma = FakeGemma()
    override(gemma)
    try:
        body = post(client, challenge_id=challenge.id).json()
    finally:
        app.dependency_overrides.clear()
    assert "looks like a face" in gemma.calls[0]["prompt"]
    assert body["visual_description"]


def test_unknown_challenge_id_is_ignored_not_fatal(client) -> None:
    gemma = FakeGemma()
    override(gemma)
    try:
        response = post(client, challenge_id="00000000-0000-4000-8000-000000000000")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "No challenge context" in gemma.calls[0]["prompt"]


def test_another_users_challenge_is_not_used(client, db) -> None:
    other = "22222222-2222-4222-8222-222222222222"
    repo.get_or_create_user(db, other)
    challenge = repo.add_challenge(
        db,
        user_id=other,
        title="Secret",
        prompt="Find something private.",
        category="nature",
        difficulty=2,
        estimated_minutes=20,
    )
    gemma = FakeGemma()
    override(gemma)
    try:
        post(client, challenge_id=challenge.id)
    finally:
        app.dependency_overrides.clear()
    assert "No challenge context" in gemma.calls[0]["prompt"]


def test_model_failure_returns_502_without_trace(client) -> None:
    from app.errors import GemmaError

    override(FakeGemma(error=GemmaError("The AI couldn't look at that photo.")))
    try:
        response = post(client)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502
    assert "Traceback" not in response.text
