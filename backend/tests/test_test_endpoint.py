"""Tests for the Gemma connection diagnostic endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.test_routes import get_service
from app.config import get_settings
from app.errors import GemmaError
from app.main import app
from app.schemas.ai import ChallengeDraft
from app.services.gemma import GemmaService


def override_with(service: GemmaService):
    return lambda: service


class Stub:
    def __init__(self, *, text_result=None, structured_result=None):
        self.text_result = text_result
        self.structured_result = structured_result

    def generate_text(self, prompt, *, system=None):
        if isinstance(self.text_result, Exception):
            raise self.text_result
        return self.text_result

    def generate_structured(self, prompt, schema, *, system=None):
        if isinstance(self.structured_result, Exception):
            raise self.structured_result
        return self.structured_result

    model = "stub-model"


client = TestClient(app)


def test_returns_success_when_both_calls_work() -> None:
    stub = Stub(
        text_result="Go outside.",
        structured_result=ChallengeDraft(
            title="T", prompt="P", category="color", difficulty=1, estimated_minutes=10
        ),
    )
    app.dependency_overrides[get_service] = override_with(stub)
    try:
        body = client.post("/api/test/gemma").json()
    finally:
        app.dependency_overrides.clear()
    assert body["success"] is True
    assert body["structured_ok"] is True


def test_reports_failure_without_api_key() -> None:
    """A missing key must be a clean diagnostic, never a stack trace."""
    stub = Stub(text_result=GemmaError("not configured", detail="GEMINI_API_KEY is not set"))
    app.dependency_overrides[get_service] = override_with(stub)
    try:
        response = client.post("/api/test/gemma")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "GEMINI_API_KEY" in body["error"]
    assert "Traceback" not in body["error"]


def test_partial_failure_is_reported() -> None:
    stub = Stub(text_result="ok", structured_result=GemmaError("bad json"))
    app.dependency_overrides[get_service] = override_with(stub)
    try:
        body = client.post("/api/test/gemma").json()
    finally:
        app.dependency_overrides.clear()
    assert body["success"] is False
    assert body["sample"] == "ok"
    assert "structured output failed" in body["error"]


def test_settings_endpoint_contract() -> None:
    assert get_settings().gemma_model
