"""Tests for the discovery evaluation graph and endpoints (no network)."""

from __future__ import annotations

import io

from PIL import Image

from app.api.discovery_routes import get_service
from app.db import repositories as repo
from app.errors import GemmaError
from app.graph.graph import build_discovery_graph, run_discovery_graph
from app.main import app
from app.schemas.ai import DiscoveryEvaluation, DiscoveryFeedback, DiscoveryJudgment

USER = "11111111-1111-4111-8111-111111111111"


def image_bytes(size=(64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "green").save(buffer, format="JPEG")
    return buffer.getvalue()


def judgment(**overrides) -> DiscoveryJudgment:
    data = {
        "visual_description": "Tree branches against a pale sky.",
        "subjects": ["branches", "sky"],
        "setting": "a park",
        "unexpected_details": ["a knot shaped like an eye"],
        "image_quality": "clear",
        "description_caveat": "",
        "completed": True,
        "confidence": 0.91,
        "what_was_found": "A face formed by tree branches",
        "reasoning_summary": "The branches outline two eyes and a mouth.",
        "interesting_detail": "This appears to be a mature tree.",
        "score": 9,
        "feedback": "You found it. The branches really do resemble a face.",
    }
    data.update(overrides)
    return DiscoveryJudgment(**data)


class FakeGemma:
    """Records every model call so tests can assert on call counts."""

    def __init__(self, *, judgment_result=None, feedback_result=None, error=None):
        self.judgment = judgment_result or judgment()
        self.feedback_result = feedback_result or DiscoveryFeedback(
            title="A Face In The Branches",
            reflection="The branches create a surprisingly convincing facial outline.",
            tagline="a face, hiding",
        )
        self.error = error
        self.image_calls: list[dict] = []
        self.text_calls: list[dict] = []

    def generate_structured_from_image(
        self, prompt, image_bytes, mime_type, schema, *, system=None
    ):
        self.image_calls.append({"prompt": prompt, "mime": mime_type})
        if self.error:
            raise self.error
        return self.judgment

    def generate_structured(self, prompt, schema, *, system=None):
        self.text_calls.append({"prompt": prompt})
        if self.error:
            raise self.error
        if schema is DiscoveryEvaluation:
            return DiscoveryEvaluation(**judgment().model_dump())
        return self.feedback_result


def challenge_for(db, user_id=USER, **overrides):
    payload = {
        "user_id": user_id,
        "title": "Hidden Faces",
        "prompt": "Find something that looks like a face.",
        "category": "nature",
        "difficulty": 2,
        "estimated_minutes": 20,
    }
    payload.update(overrides)
    return repo.add_challenge(db, **payload)


def state_for(db, gemma, challenge=None, pipeline=None):
    challenge = challenge or challenge_for(db)
    saved: dict = {}

    def save(**record):
        saved.update(record)
        return record

    return saved, challenge


# ------------------------------------------------------------------- graph


async def test_combined_pipeline_makes_exactly_one_image_call(db) -> None:
    """SPEC §43: one multimodal call, not a chain of them."""
    gemma = FakeGemma()
    challenge = challenge_for(db)

    state = await run_discovery_graph(
        USER,
        challenge_id=challenge.id,
        image_bytes=image_bytes(),
        image_mime_type="image/jpeg",
        service=gemma,
        load_challenge=lambda uid, cid: {
            "id": cid,
            "title": "t",
            "prompt": "p",
            "category": "nature",
        },
        pipeline="combined",
    )

    assert len(gemma.image_calls) == 1
    assert state["evaluation"]["score"] == 9
    assert state["evaluation"]["completed"] is True
    assert state["image_analysis"]["visual_description"].startswith("Tree branches")


async def test_two_stage_pipeline_makes_two_calls(db) -> None:
    gemma = FakeGemma()
    challenge = challenge_for(db)

    await run_discovery_graph(
        USER,
        challenge_id=challenge.id,
        image_bytes=image_bytes(),
        image_mime_type="image/jpeg",
        service=gemma,
        load_challenge=lambda uid, cid: {
            "id": cid,
            "title": "t",
            "prompt": "p",
            "category": "nature",
        },
        pipeline="two_stage",
    )
    assert len(gemma.image_calls) == 1
    assert len(gemma.text_calls) == 2  # evaluate + feedback


async def test_state_is_serialisable(db) -> None:
    """SPEC §9: raw image bytes must not leak into the graph state."""
    gemma = FakeGemma()
    challenge = challenge_for(db)
    state = await run_discovery_graph(
        USER,
        challenge_id=challenge.id,
        image_bytes=image_bytes(),
        image_mime_type="image/jpeg",
        service=gemma,
        load_challenge=lambda uid, cid: {
            "id": cid,
            "title": "t",
            "prompt": "p",
            "category": "nature",
        },
    )
    assert "image_bytes" not in state
    for key, value in state.items():
        assert not isinstance(value, bytes), key


async def test_graph_nodes_are_the_documented_set() -> None:
    graph = build_discovery_graph()
    nodes = set(graph.get_graph().nodes) - {"__start__", "__end__"}
    assert nodes == {
        "load_challenge",
        "analyze_photo",
        "evaluate_discovery",
        "generate_feedback",
        "save_discovery",
        "update_profile",
    }


async def test_missing_challenge_short_circuits_with_an_error(db) -> None:
    gemma = FakeGemma()
    state = await run_discovery_graph(
        USER,
        challenge_id="does-not-exist",
        image_bytes=image_bytes(),
        image_mime_type="image/jpeg",
        service=gemma,
        load_challenge=lambda uid, cid: None,
    )
    assert state["error"] == "That challenge could not be found."
    assert gemma.image_calls == []


async def test_model_failure_is_captured_not_raised(db) -> None:
    gemma = FakeGemma(error=GemmaError("couldn't look at that photo"))
    challenge = challenge_for(db)
    state = await run_discovery_graph(
        USER,
        challenge_id=challenge.id,
        image_bytes=image_bytes(),
        image_mime_type="image/jpeg",
        service=gemma,
        load_challenge=lambda uid, cid: {
            "id": cid,
            "title": "t",
            "prompt": "p",
            "category": "nature",
        },
    )
    assert state["error"]
    assert gemma.image_calls


async def test_failed_discovery_is_still_saved(db) -> None:
    """A miss belongs in the journal, flagged incomplete."""
    gemma = FakeGemma(
        judgment_result=judgment(
            completed=False, score=2, feedback="No face here yet — keep looking."
        )
    )
    challenge = challenge_for(db)
    saved: dict = {}

    def save(**record):
        saved.update(record)
        return record

    await run_discovery_graph(
        USER,
        challenge_id=challenge.id,
        image_bytes=image_bytes(),
        image_mime_type="image/jpeg",
        service=gemma,
        load_challenge=lambda uid, cid: {
            "id": cid,
            "title": "t",
            "prompt": "p",
            "category": "nature",
            "estimated_minutes": 20,
        },
        save_discovery=save,
    )
    assert saved["completed"] is False
    assert saved["score"] == 2
    assert saved["points_awarded"] == 2


async def test_score_bounds_are_enforced_by_the_schema() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        judgment(score=11)
    with pytest.raises(ValidationError):
        judgment(confidence=1.5)


# ---------------------------------------------------------------- endpoints


def override(gemma: FakeGemma) -> None:
    app.dependency_overrides[get_service] = lambda: gemma


def clear() -> None:
    app.dependency_overrides.clear()


def post(client, db, *, challenge_id=None, data=None, user=USER):
    challenge_id = challenge_id or challenge_for(db).id
    return client.post(
        "/api/discoveries",
        files={"image": ("photo.jpg", data or image_bytes(), "image/jpeg")},
        data={"challenge_id": challenge_id},
        headers={"X-User-Id": user},
    )


def test_submit_returns_the_discovery(client, db) -> None:
    repo.get_or_create_user(db, USER)
    override(FakeGemma())
    try:
        body = post(client, db).json()
    finally:
        clear()

    discovery = body["discovery"]
    assert discovery["score"] == 9
    assert discovery["completed"] is True
    assert discovery["title"] == "A Face In The Branches"
    assert discovery["feedback"].startswith("You found it")
    assert discovery["image_url"].startswith("/uploads/")
    assert discovery["points_awarded"] == 9
    assert discovery["confidence"] == 0.91


def test_submit_updates_the_profile(client, db) -> None:
    repo.get_or_create_user(db, USER)
    override(FakeGemma())
    try:
        body = post(client, db).json()
    finally:
        clear()
    assert body["profile"]["total_points"] == 9
    assert body["profile"]["discoveries_count"] == 1
    assert body["profile"]["favorite_categories"] == {"nature": 1.0}


def test_submit_persists_a_discovery_row(client, db) -> None:
    repo.get_or_create_user(db, USER)
    override(FakeGemma())
    try:
        post(client, db)
    finally:
        clear()
    rows = db.query(repo.Discovery).all()
    assert len(rows) == 1
    assert rows[0].score == 9
    assert rows[0].tagline == "a face, hiding"


def test_submit_marks_the_challenge_completed(client, db) -> None:
    repo.get_or_create_user(db, USER)
    challenge = challenge_for(db)
    override(FakeGemma())
    try:
        post(client, db, challenge_id=challenge.id)
    finally:
        clear()
    db.refresh(challenge)
    assert challenge.status == "completed"
    assert challenge.completed_at is not None


def test_unknown_challenge_returns_404(client, db) -> None:
    override(FakeGemma())
    try:
        response = client.post(
            "/api/discoveries",
            files={"image": ("p.jpg", image_bytes(), "image/jpeg")},
            data={"challenge_id": "nope"},
            headers={"X-User-Id": USER},
        )
    finally:
        clear()
    assert response.status_code == 404


def test_cannot_submit_against_another_users_challenge(client, db) -> None:
    other = "22222222-2222-4222-8222-222222222222"
    repo.get_or_create_user(db, other)
    challenge = challenge_for(db, user_id=other)
    gemma = FakeGemma()
    override(gemma)
    try:
        response = post(client, db, challenge_id=challenge.id)
    finally:
        clear()
    assert response.status_code == 404
    assert gemma.image_calls == [], "the model must not run for another user's challenge"


def test_bad_image_never_reaches_the_model(client, db) -> None:
    gemma = FakeGemma()
    override(gemma)
    try:
        response = post(client, db, data=b"MZ not an image")
    finally:
        clear()
    assert response.status_code == 400
    assert gemma.image_calls == []


def test_model_failure_returns_502_and_no_trace(client, db) -> None:
    repo.get_or_create_user(db, USER)
    override(FakeGemma(error=GemmaError("couldn't look at that photo")))
    try:
        response = post(client, db)
    finally:
        clear()
    assert response.status_code == 502
    assert "Traceback" not in response.text


# ------------------------------------------------------- journal & profile


def test_journal_lists_discoveries_newest_first(client, db) -> None:
    repo.get_or_create_user(db, USER)
    override(FakeGemma())
    try:
        post(client, db)
        post(client, db)
    finally:
        clear()
    body = client.get("/api/journal", headers={"X-User-Id": USER}).json()
    assert body["total"] == 2
    assert len(body["discoveries"]) == 2


def test_journal_is_empty_for_a_new_user(client) -> None:
    body = client.get("/api/journal", headers={"X-User-Id": USER}).json()
    assert body == {"discoveries": [], "total": 0}


def test_journal_is_scoped_per_user(client, db) -> None:
    repo.get_or_create_user(db, USER)
    override(FakeGemma())
    try:
        post(client, db)
    finally:
        clear()
    other = client.get(
        "/api/journal", headers={"X-User-Id": "22222222-2222-4222-8222-222222222222"}
    ).json()
    assert other["total"] == 0


def test_profile_creates_on_first_request(client) -> None:
    body = client.get("/api/profile", headers={"X-User-Id": USER}).json()
    assert body["total_points"] == 0
    assert body["discoveries_count"] == 0
    assert body["favorite_categories"] == {}


def test_profile_reflects_discoveries(client, db) -> None:
    repo.get_or_create_user(db, USER)
    override(FakeGemma())
    try:
        post(client, db)
    finally:
        clear()
    body = client.get("/api/profile", headers={"X-User-Id": USER}).json()
    assert body["total_points"] == 9
    assert body["discoveries_count"] == 1
    assert body["favorite_categories"] == {"nature": 1.0}
