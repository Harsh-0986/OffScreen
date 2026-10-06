"""Tests for the photo upload + analysis endpoint (no network)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.api.photo_routes import get_service
from app.db import repositories as repo
from app.errors import GemmaError
from app.main import app
from app.schemas.ai import PhotoAnalysis


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
        self.calls: list[dict] = []

    def generate_structured_from_image(
        self, prompt, image_bytes, mime_type, schema, *, system=None
    ):
        self.calls.append({"prompt": prompt, "bytes": image_bytes, "mime": mime_type})
        if self.error:
            raise self.error
        return self.analysis

    def generate_structured(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("analysis must use the multimodal call")


@pytest.fixture
def gemma():
    """A stub model, swapped in for the duration of the test."""
    fake = FakeGemma()
    app.dependency_overrides[get_service] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def account(make_user):
    user, headers = make_user()
    return user, headers


def post(
    client,
    headers,
    *,
    data=None,
    filename="photo.jpg",
    content_type="image/jpeg",
    **form,
):
    return client.post(
        "/api/photos/analyze",
        files={"image": (filename, data if data is not None else image_bytes(), content_type)},
        data=form,
        headers=headers,
    )


# ------------------------------------------------------------- happy path


def test_returns_visual_description(client, gemma, account) -> None:
    _, headers = account
    body = post(client, headers).json()
    assert body["visual_description"] == "A mossy wall beside a path."
    assert body["subjects"] == ["moss", "wall"]


def test_phase_three_returns_no_scoring(client, gemma, account) -> None:
    """Scoring arrives in Phase 4 via /api/discoveries, not here."""
    _, headers = account
    assert "score" not in post(client, headers).json()


def test_upload_metadata_is_returned(client, gemma, account) -> None:
    _, headers = account
    body = post(client, headers, data=image_bytes((4000, 3000))).json()
    assert body["width"] == 1280
    assert body["resized"] is True
    assert body["original_bytes"] > 0


def test_model_receives_the_resized_jpeg(client, gemma, account) -> None:
    _, headers = account
    post(client, headers, data=image_bytes((4000, 3000)))
    assert gemma.calls[0]["mime"] == "image/jpeg"
    assert len(gemma.calls[0]["bytes"]) < 1_000_000


# --------------------------------------------------------------- rejection


def test_rejects_non_image_upload(client, gemma, account) -> None:
    _, headers = account
    response = post(client, headers, data=b"MZ executable", filename="virus.jpg")
    assert response.status_code == 400
    assert "Traceback" not in response.text
    assert gemma.calls == []


def test_rejects_unsupported_content_type(client, gemma, account) -> None:
    _, headers = account
    response = post(client, headers, content_type="application/pdf")
    assert response.status_code == 400
    assert gemma.calls == []


def test_requires_authentication(client, gemma) -> None:
    assert post(client, None).status_code == 401


def test_rejects_upload_over_the_size_cap(client, gemma, account) -> None:
    """The cap is enforced while streaming, before the model is ever called."""
    _, headers = account
    from app.api import photo_routes

    original = photo_routes.get_settings

    class Capped:
        max_image_bytes = 1024
        upload_path = original().upload_path

    photo_routes.get_settings = lambda: Capped()  # type: ignore[assignment]
    try:
        response = post(client, headers, data=image_bytes((900, 900)))
    finally:
        photo_routes.get_settings = original  # type: ignore[assignment]

    assert response.status_code == 400
    assert "too large" in response.json()["detail"]
    assert gemma.calls == [], "the model must not be called for a rejected upload"


# -------------------------------------------------------- challenge context


def test_challenge_context_is_passed_when_id_is_known(client, gemma, account, db) -> None:
    user, headers = account
    challenge = repo.add_challenge(
        db,
        user_id=user.id,
        title="A Face",
        prompt="Find something that looks like a face.",
        category="nature",
        difficulty=2,
        estimated_minutes=20,
    )
    body = post(client, headers, challenge_id=challenge.id).json()
    assert "looks like a face" in gemma.calls[0]["prompt"]
    assert body["visual_description"]


def test_unknown_challenge_id_is_ignored_not_fatal(client, gemma, account) -> None:
    _, headers = account
    response = post(client, headers, challenge_id="00000000-0000-4000-8000-000000000000")
    assert response.status_code == 200
    assert "No challenge context" in gemma.calls[0]["prompt"]


def test_another_users_challenge_is_not_used(client, gemma, make_user, db) -> None:
    _, headers = make_user()
    victim, _ = make_user("victim@example.com")
    challenge = repo.add_challenge(
        db,
        user_id=victim.id,
        title="Secret",
        prompt="Find something private.",
        category="nature",
        difficulty=2,
        estimated_minutes=20,
    )
    post(client, headers, challenge_id=challenge.id)
    assert "No challenge context" in gemma.calls[0]["prompt"]


# ------------------------------------------------------------ model failure


def test_model_failure_returns_502_without_trace(client, account) -> None:
    _, headers = account
    app.dependency_overrides[get_service] = lambda: FakeGemma(
        error=GemmaError("The AI couldn't look at that photo.")
    )
    try:
        response = post(client, headers)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502
    assert "Traceback" not in response.text
