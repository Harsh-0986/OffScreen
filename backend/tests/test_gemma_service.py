"""Tests for the Gemma service using a fake model client (no network)."""

from __future__ import annotations

import pytest

from app.errors import GemmaError, SchemaValidationError
from app.schemas.ai import ChallengeDraft
from app.services.gemma import GemmaService


class FakeStructuredClient:
    """Stand-in for the Runnable returned by `with_structured_output`."""

    def __init__(self, payload, counter: dict | None = None):
        self.payload = payload
        self.counter = counter if counter is not None else {}
        self.messages: list = []

    @property
    def calls(self) -> int:
        return self.counter.get("calls", 0)

    def invoke(self, messages):
        self.counter["calls"] = self.calls + 1
        self.messages.append(messages)
        self.counter.setdefault("messages", self.messages)
        payload = self.payload(self.calls) if callable(self.payload) else self.payload
        if isinstance(payload, Exception):
            raise payload
        return payload


class FakeClient(FakeStructuredClient):
    """Stand-in for a LangChain chat model."""

    def with_structured_output(self, schema):
        return FakeStructuredClient(self.payload, self.counter)


class TextResponse:
    def __init__(self, text: str) -> None:
        self.content = text


class ListContentResponse:
    def __init__(self, blocks) -> None:
        self.content = blocks


def test_generate_text_returns_content() -> None:
    service = GemmaService(client=FakeClient(TextResponse("Go find a shadow.")))
    assert service.generate_text("prompt") == "Go find a shadow."


def test_generate_text_flattens_content_blocks() -> None:
    client = FakeClient(
        ListContentResponse([{"type": "text", "text": "hello "}, {"type": "text", "text": "world"}])
    )
    assert GemmaService(client=client).generate_text("prompt") == "hello world"


def test_generate_text_raises_on_empty_response() -> None:
    service = GemmaService(client=FakeClient(TextResponse("   ")))
    with pytest.raises(GemmaError):
        service.generate_text("prompt")


def test_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(
        lambda call: RuntimeError("429 rate limited") if call == 1 else TextResponse("ok")
    )
    service = GemmaService(client=client, max_retries=2)
    monkeypatch.setattr("app.services.gemma.time.sleep", lambda _s: None)
    assert service.generate_text("prompt") == "ok"
    assert client.calls == 2


def test_gives_up_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(lambda call: RuntimeError("503 model unavailable"))
    service = GemmaService(client=client, max_retries=1)
    monkeypatch.setattr("app.services.gemma.time.sleep", lambda _s: None)
    with pytest.raises(GemmaError) as exc:
        service.generate_text("prompt")
    assert client.calls == 2
    assert exc.value.status_code == 502


def test_safety_block_is_not_retried() -> None:
    client = FakeClient(lambda call: RuntimeError("blocked due to safety_settings"))
    service = GemmaService(client=client, max_retries=3)
    with pytest.raises(GemmaError) as exc:
        service.generate_text("prompt")
    assert client.calls == 1
    assert "different one" in exc.value.message


def test_generate_structured_validates_payload() -> None:
    payload = {
        "title": "Symmetry",
        "prompt": "Find something symmetrical.",
        "category": "shapes",
        "difficulty": 2,
        "estimated_minutes": 20,
    }
    draft = GemmaService(client=FakeClient(payload)).generate_structured("p", ChallengeDraft)
    assert isinstance(draft, ChallengeDraft)
    assert draft.category == "shapes"


def test_generate_structured_parses_stringified_json() -> None:
    payload = (
        '```json\n{"title":"A","prompt":"B","category":"color",'
        '"difficulty":1,"estimated_minutes":10}\n```'
    )
    draft = GemmaService(client=FakeClient(TextResponse(payload))).generate_structured(
        "p", ChallengeDraft
    )
    assert draft.title == "A"


def test_generate_structured_rejects_bad_schema() -> None:
    service = GemmaService(client=FakeClient({"title": "A"}))
    with pytest.raises(SchemaValidationError):
        service.generate_structured("p", ChallengeDraft)


def test_generate_structured_rejects_invalid_json() -> None:
    service = GemmaService(client=FakeClient(TextResponse("not json at all")))
    with pytest.raises(SchemaValidationError):
        service.generate_structured("p", ChallengeDraft)


def test_structured_falls_back_to_plain_call() -> None:
    """If the structured runner fails, the plain client + JSON instruction is used."""

    class StructuredRaises(FakeClient):
        def with_structured_output(self, schema):

            class Raiser:
                def invoke(self, messages):
                    raise RuntimeError("structured output unsupported")

            return Raiser()

    client = StructuredRaises(
        {
            "title": "A",
            "prompt": "B",
            "category": "color",
            "difficulty": 1,
            "estimated_minutes": 10,
        }
    )
    draft = GemmaService(client=client, max_retries=0).generate_structured("p", ChallengeDraft)
    assert draft.prompt == "B"


def test_schema_hint_lists_keys_and_enum() -> None:
    from app.services.gemma import _schema_hint

    hint = _schema_hint(ChallengeDraft)
    assert '"title"' in hint
    assert '"difficulty"' in hint
    assert '"color"' in hint  # rendered from the enum


def test_repairs_a_bad_response_then_succeeds() -> None:
    """A schema violation earns exactly one repair attempt."""
    good = {
        "title": "A",
        "prompt": "B",
        "category": "color",
        "difficulty": 1,
        "estimated_minutes": 10,
    }
    client = FakeClient(lambda call: {"title": "A", "mystery": 1} if call == 1 else good)
    draft = GemmaService(client=client, max_retries=0).generate_structured("p", ChallengeDraft)
    assert draft.category == "color"
    assert client.calls == 2


def test_gives_up_after_repair_attempts() -> None:
    client = FakeClient(lambda call: {"title": "A", "mystery": 1})
    with pytest.raises(SchemaValidationError):
        GemmaService(client=client, max_retries=0).generate_structured("p", ChallengeDraft)
    assert client.calls == 2  # original + one repair


def test_tooling_mode_uses_structured_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.gemma.STRUCTURED_OUTPUT_MODE", "tooling")
    good = {
        "title": "A",
        "prompt": "B",
        "category": "color",
        "difficulty": 1,
        "estimated_minutes": 10,
    }
    client = FakeClient(good)
    draft = GemmaService(client=client, max_retries=0).generate_structured("p", ChallengeDraft)
    assert draft.title == "A"


def test_image_input_uses_inline_data_url() -> None:
    """The structured runner receives a text part plus an inline data-URL image."""
    payload = {
        "title": "A",
        "prompt": "B",
        "category": "color",
        "difficulty": 1,
        "estimated_minutes": 10,
    }
    client = FakeClient(payload)
    service = GemmaService(client=client, max_retries=0)
    service.generate_structured_from_image("prompt", b"bytes", "image/png", ChallengeDraft)

    # the multimodal message is the one carrying list content
    messages = next(
        m for batch in client.counter["messages"] for m in batch if isinstance(m.content, list)
    )
    content = messages.content
    assert content[0]["type"] == "text"
    assert content[1]["image_url"].startswith("data:image/png;base64,")


def test_image_input_rejects_unsupported_mime() -> None:
    service = GemmaService(client=FakeClient(None))
    with pytest.raises(GemmaError):
        service.generate_structured_from_image("p", b"x", "image/gif", ChallengeDraft)
