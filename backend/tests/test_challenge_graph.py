"""Tests for the challenge generation graph and endpoint (no network)."""

from __future__ import annotations

from datetime import date

import pytest

from app.api.challenge_routes import get_service
from app.constants import CHALLENGE_CATEGORIES
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
    # the deterministically chosen category wins over whatever the model returned
    assert state["current_challenge"]["category"] in CHALLENGE_CATEGORIES
    assert state["current_challenge"]["personalization_mode"] in {"familiar", "exploration"}


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


def test_generate_endpoint_returns_challenge(client, user_and_headers) -> None:
    _, headers = user_and_headers
    override(FakeGemma(VALID_DRAFT))
    try:
        body = client.post("/api/challenges/generate", headers=headers).json()
    finally:
        app.dependency_overrides.clear()
    assert body["challenge"]["title"] == "Branches With A Face"
    assert body["challenge"]["estimated_minutes"] == 20


def test_generate_endpoint_requires_authentication(client) -> None:
    """There is no anonymous access any more."""
    override(FakeGemma(VALID_DRAFT))
    try:
        response = client.post("/api/challenges/generate")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401


def test_generate_endpoint_rejects_a_forged_token(client, user_and_headers) -> None:
    _, _ = user_and_headers
    override(FakeGemma(VALID_DRAFT))
    try:
        response = client.post(
            "/api/challenges/generate", headers={"Authorization": "Bearer not.a.token"}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
    assert "Traceback" not in response.text


def test_generate_endpoint_rejects_a_tampered_signature(client, user_and_headers) -> None:
    _, headers = user_and_headers
    token = headers["Authorization"].split(".", 3)[1]
    tampered = dict(headers)
    tampered["Authorization"] = f"Bearer {token}x.1.deadbeef"
    override(FakeGemma(VALID_DRAFT))
    try:
        response = client.post("/api/challenges/generate", headers=tampered)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401


def test_generate_endpoint_surfaces_model_failure_as_502(client, user_and_headers) -> None:
    _, headers = user_and_headers
    override(FakeGemma(error=GemmaError("model unavailable")))
    try:
        response = client.post("/api/challenges/generate", headers=headers)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502


def test_each_user_gets_their_own_challenge(client, make_user) -> None:
    _, headers_a = make_user("a@example.com")
    _, headers_b = make_user("b@example.com")
    override(FakeGemma(VALID_DRAFT))
    try:
        a = client.post("/api/challenges/generate", headers=headers_a).json()
        b = client.post("/api/challenges/generate", headers=headers_b).json()
    finally:
        app.dependency_overrides.clear()
    assert a["challenge"]["id"] != b["challenge"]["id"]


@pytest.mark.parametrize("path", ["/api/challenges/generate", "/api/challenges/today"])
def test_endpoints_require_authentication(path: str, client) -> None:
    override(FakeGemma(VALID_DRAFT))
    try:
        response = client.request(
            "POST" if "generate" in path else "GET",
            path,
            headers={"Authorization": "Bearer ../../etc/passwd"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401


# ---------------------------------------------------------- personalization


async def test_prompt_carries_the_chosen_category_constraint() -> None:
    gemma = FakeGemma(VALID_DRAFT)
    await run_challenge_graph(
        "u1",
        service=gemma,
        select_category=lambda profile, seed=None: ("shapes", "exploration"),
    )
    prompt = gemma.prompts[0]
    assert '"shapes"' in prompt
    assert "MUST be exactly" in prompt


async def test_model_cannot_override_the_chosen_category() -> None:
    """The model returned nature; the deterministic pick was shapes."""
    gemma = FakeGemma(VALID_DRAFT.model_copy(update={"category": "nature"}))
    state = await run_challenge_graph(
        "u1",
        service=gemma,
        select_category=lambda profile, seed=None: ("shapes", "exploration"),
    )
    assert state["current_challenge"]["category"] == "shapes"


async def test_category_override_stays_schema_validated() -> None:
    """An impossible category must not slip through the override path."""
    gemma = FakeGemma(VALID_DRAFT)
    state = await run_challenge_graph(
        "u1",
        service=gemma,
        select_category=lambda profile, seed=None: ("not_a_real_category", "exploration"),
    )
    # An invalid override is refused; the model's own category survives instead of
    # a ValidationError escaping the graph.
    assert state["current_challenge"]["category"] == "nature"
    assert "error" not in state


async def test_consecutive_challenges_are_never_identical() -> None:
    """SPEC §35 acceptance: two consecutive challenges must differ.

    Simulates several days of generation for one user, each day's history
    including every previously generated title.
    """
    history: list[str] = []
    titles = []
    for _day in range(6):
        gemma = FakeGemma(VALID_DRAFT)
        state = await run_challenge_graph(
            "u1",
            service=gemma,
            load_history=lambda uid, h=list(history): list(h),
            select_category=lambda profile, seed=None: ("creativity", "exploration"),
        )
        title = state["current_challenge"]["title"]
        titles.append(title)
        history.append(title)

    assert len(set(titles)) == 1, "regeneration should force a different title each day"


async def test_duplicate_title_triggers_exactly_one_regeneration() -> None:
    gemma = FakeGemma(VALID_DRAFT)
    await run_challenge_graph(
        "u1",
        service=gemma,
        load_history=lambda uid: ["Branches With A Face"],
    )
    assert len(gemma.prompts) == 2
    assert "already given" in gemma.prompts[1]


async def test_regenerated_draft_is_also_category_constrained() -> None:
    other = VALID_DRAFT.model_copy(update={"category": "color"})
    gemma = FakeGemma(other, other)
    state = await run_challenge_graph(
        "u1",
        service=gemma,
        load_history=lambda uid: ["Branches With A Face"],
        select_category=lambda profile, seed=None: ("shapes", "exploration"),
    )
    assert state["current_challenge"]["category"] == "shapes"


def test_prompt_lists_favourite_categories_with_weights() -> None:
    from app.prompts.challenge_generation import build_user_prompt

    prompt = build_user_prompt(
        {"user_profile": {"favorite_categories": {"nature": 7.0}}, "recent_challenges": []}
    )
    assert "nature (7.0)" in prompt
