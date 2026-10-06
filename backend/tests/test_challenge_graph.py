"""Tests for the challenge generation graph and endpoint (no network)."""

from __future__ import annotations

from datetime import date

import pytest

from app.api.challenge_routes import get_service
from app.errors import GemmaError
from app.graph.graph import build_challenge_graph, run_challenge_graph
from app.graph.nodes import load_context
from app.main import app
from app.schemas.ai import ChallengeDraft

VALID_DRAFT = ChallengeDraft(
    title="Branches With A Face",
    prompt="Find something that looks like a face.",
    category="nature",
    difficulty=2,
    estimated_minutes=20,
)


class FakeGemma:
    """Stands in for GemmaService, recording the prompts it receives."""

    def __init__(self, *drafts, error: Exception | None = None):
        self.drafts = list(drafts) or [VALID_DRAFT]
        self.error = error
        self.prompts: list[str] = []
        self.systems: list[str | None] = []

    def generate_structured(self, prompt, schema, *, system=None):
        self.prompts.append(prompt)
        self.systems.append(system)
        if self.error:
            raise self.error
        return self.drafts[min(len(self.prompts) - 1, len(self.drafts) - 1)]


def override(service: FakeGemma):
    app.dependency_overrides[get_service] = lambda: service
    return service


# ------------------------------------------------------------------- context


def test_load_context_defaults_to_new_user() -> None:
    update = load_context({"user_id": "u1"}, now=date(2026, 10, 6))
    assert update["user_profile"]["discoveries_count"] == 0
    assert update["challenge_history"] == []
    assert update["context_date"] == "2026-10-06"


def test_load_context_uses_injected_loaders() -> None:
    update = load_context(
        {"user_id": "u1"},
        load_profile=lambda uid: {"id": uid, "favorite_categories": {"nature": 7}},
        load_history=lambda uid: ["old one", "old two"],
        load_discoveries=lambda uid: ["a mossy wall"],
    )
    assert update["challenge_history"] == ["old one", "old two"]
    assert update["recent_discoveries"] == ["a mossy wall"]


def test_load_context_limits_history_window() -> None:
    update = load_context({"user_id": "u"}, load_history=lambda uid: [f"c{i}" for i in range(50)])
    assert len(update["challenge_history"]) == 8


# --------------------------------------------------------------------- graph


async def test_graph_produces_a_validated_challenge() -> None:
    gemma = FakeGemma(VALID_DRAFT)
    state = await run_challenge_graph("u1", service=gemma)
    assert "error" not in state
    assert state["current_challenge"]["title"] == "Branches With A Face"
    assert state["current_challenge"]["category"] == "nature"


async def test_graph_passes_history_into_the_prompt() -> None:
    gemma = FakeGemma(VALID_DRAFT)
    await run_challenge_graph(
        "u1",
        service=gemma,
        load_history=lambda uid: ["Find something symmetrical"],
    )
    assert "Find something symmetrical" in gemma.prompts[0]


async def test_graph_regenerates_a_duplicate_title() -> None:
    """A challenge identical to a previous one is regenerated (SPEC §35)."""
    gemma = FakeGemma(VALID_DRAFT, VALID_DRAFT.model_copy(update={"title": "A Different Tree"}))
    state = await run_challenge_graph(
        "u1", service=gemma, load_history=lambda uid: ["Branches With A Face"]
    )
    assert len(gemma.prompts) == 2
    assert state["current_challenge"]["title"] == "A Different Tree"


async def test_graph_reports_errors_without_raising() -> None:
    gemma = FakeGemma(error=GemmaError("nope", detail="rate limited"))
    state = await run_challenge_graph("u1", service=gemma)
    assert state["error"] == "nope"


def test_graph_shape_is_linear() -> None:
    """The compiled graph exposes exactly the two documented nodes."""
    graph = build_challenge_graph()
    nodes = set(graph.get_graph().nodes) - {"__start__", "__end__"}
    assert nodes == {"load_context", "generate_challenge"}


# ------------------------------------------------------------------- endpoint


def test_generate_endpoint_returns_challenge(client) -> None:
    override(FakeGemma(VALID_DRAFT))
    try:
        body = client.post("/api/challenges/generate", headers={"X-User-Id": _uuid()}).json()
    finally:
        app.dependency_overrides.clear()
    assert body["challenge"]["title"] == "Branches With A Face"
    assert body["challenge"]["estimated_minutes"] == 20


def test_generate_endpoint_works_without_a_user_header(client) -> None:
    """A plain curl with no identity still returns a challenge."""
    override(FakeGemma(VALID_DRAFT))
    try:
        response = client.post("/api/challenges/generate")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200


def test_generate_endpoint_rejects_a_bad_user_id(client) -> None:
    override(FakeGemma(VALID_DRAFT))
    try:
        response = client.post("/api/challenges/generate", headers={"X-User-Id": "not-a-uuid"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "UUID" in response.json()["detail"]
    assert "Traceback" not in response.text


def test_generate_endpoint_surfaces_model_failure_as_502(client) -> None:
    override(FakeGemma(error=GemmaError("model unavailable")))
    try:
        response = client.post("/api/challenges/generate")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502


def _uuid() -> str:
    return "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize("path", ["/api/challenges/generate", "/api/challenges/today"])
def test_endpoints_reject_invalid_user_id(path: str, client) -> None:
    """Path-traversal style identities are rejected before any lookup."""
    override(FakeGemma(VALID_DRAFT))
    try:
        response = client.request(
            "POST" if "generate" in path else "GET", path, headers={"X-User-Id": "../../etc/passwd"}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
