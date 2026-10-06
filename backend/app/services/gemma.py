"""Gemma service.

Single place where the model is configured, called, retried, and normalised.

Responsibilities (SPEC §23):
  - initialize the Gemini client
  - call Gemma
  - handle image input
  - enforce structured output
  - handle retries
  - normalize model responses

The client is injectable so the whole application can be tested without network
access, and so the LangGraph integration stays isolated from the vendor SDK.
"""

from __future__ import annotations

import base64
import logging
import os
import random
import time
from typing import Any, Protocol, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.errors import GemmaError, MissingAPIKeyError, SchemaValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 2
RETRY_BASE_DELAY = float(os.environ.get("GEMMA_RETRY_BASE_DELAY", "1.5"))

# How structured output is obtained.
#   "prompt"  -> describe the schema in the prompt, parse + validate locally (default)
#   "tooling" -> use the provider's with_structured_output / function calling
# Gemma on the Gemini API frequently ignores the function schema and returns its
# own key names, so the prompt path is the default. Flip this if a model is
# verified to honour the schema.
STRUCTURED_OUTPUT_MODE = os.environ.get("GEMMA_STRUCTURED_OUTPUT_MODE", "prompt")

# One extra attempt is spent asking the model to fix its own schema violation.
MAX_REPAIR_ATTEMPTS = 1

ALLOWED_IMAGE_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")

# Substrings that identify a provider-side safety block.
_SAFETY_MARKERS = ("safety", "blocked", "prohibited_content", "recitation")


class BaseChatModel(Protocol):
    """The minimal surface of a LangChain chat model that we depend on."""

    def invoke(self, messages: list[Any]) -> Any: ...


class _ImagePart(dict):
    """A Gemini image payload, shaped for `langchain-google-genai`."""


class GemmaService:
    """Thin, typed wrapper around the configured Gemma model."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float = 1.0,
        max_retries: int = DEFAULT_RETRIES,
        timeout: int = DEFAULT_TIMEOUT,
        client: BaseChatModel | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemma_model
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout
        self._client = client
        self._structured_clients: dict[int, BaseChatModel] = {}

    # ------------------------------------------------------------------ setup

    @property
    def client(self) -> BaseChatModel:
        if self._client is None:
            if not self.api_key:
                raise MissingAPIKeyError()
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._client = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=self.api_key,
                temperature=self.temperature,
                timeout=self.timeout,
            )
        return self._client

    def _structured_client(self, schema: type[BaseModel]) -> BaseChatModel:
        """Cache a structured-output client per schema.

        `with_structured_output` returns a Runnable, not a chat model, so it is
        kept out of the `BaseChatModel` protocol.
        """
        key = id(schema)
        if key not in self._structured_clients:
            try:
                self._structured_clients[key] = self.client.with_structured_output(  # type: ignore[attr-defined]
                    schema
                )
            except AttributeError as exc:  # pragma: no cover - only for stub clients
                raise GemmaError(detail=f"Client cannot enforce structured output: {exc}") from exc
        return self._structured_clients[key]

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key) or self._client is not None

    # ------------------------------------------------------------ text / JSON

    def generate_text(self, prompt: str, *, system: str | None = None) -> str:
        """Return raw text from a single-turn prompt."""
        messages = _build_messages(prompt, system)
        response = self._invoke(messages)
        text = _extract_text(response)
        if not text.strip():
            raise GemmaError(detail="Model returned an empty response")
        return text

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        """Return a Pydantic-validated object.

        The model output is never trusted: whatever the provider returns is run
        through `schema.model_validate` before it leaves this function. If the
        model ignores the required shape, it is asked once to repair its answer.
        """
        messages = _build_messages(self._with_schema(prompt, schema), system)
        return self._structured_with_repair(messages, schema)

    # ----------------------------------------------------------------- images

    def generate_structured_from_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        """One multimodal call: text prompt + inline base64 image -> schema."""
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise GemmaError(detail=f"Unsupported image mime type: {mime_type}")

        message = HumanMessage(
            content=[
                {"type": "text", "text": self._with_schema(prompt, schema)},
                _image_part(image_bytes, mime_type),
            ]
        )
        messages: list[Any] = ([SystemMessage(content=system)] if system else []) + [message]
        return self._structured_with_repair(messages, schema)

    # --------------------------------------------------------------- internal

    def _with_schema(self, prompt: str, schema: type[BaseModel]) -> str:
        """Append an explicit JSON contract to the prompt."""
        return (
            f"{prompt}\n\n"
            "Respond with a single JSON object and nothing else. No prose, no code fences.\n"
            "It must match this shape exactly, using these key names:\n"
            f"{_schema_hint(schema)}"
        )

    def _structured_with_repair(self, messages: list[Any], schema: type[T]) -> T:
        """Invoke the model and validate the result, allowing one self-repair."""
        use_tooling = STRUCTURED_OUTPUT_MODE == "tooling"

        last_error: SchemaValidationError | None = None
        for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
            try:
                raw = self._invoke(
                    messages,
                    structured=schema if use_tooling else None,
                    force_json=not use_tooling,
                )
                return _coerce(raw, schema)
            except SchemaValidationError as exc:
                last_error = exc
                if attempt == MAX_REPAIR_ATTEMPTS:
                    break
                logger.info(
                    "Schema validation failed; asking the model to repair (attempt %s)", attempt + 1
                )
                messages = messages + [
                    HumanMessage(
                        content=(
                            "That response was not valid JSON matching the required shape.\n"
                            f"Problem: {exc.detail}\n"
                            "Return corrected JSON only, using exactly these keys:\n"
                            f"{_schema_hint(schema)}"
                        )
                    )
                ]

        assert last_error is not None
        raise last_error

    def _invoke(
        self,
        messages: list[Any],
        *,
        structured: type[BaseModel] | None = None,
        force_json: bool = False,
    ) -> Any:
        runner = self._structured_client(structured) if structured is not None else self.client
        if force_json:
            messages = _with_json_instruction(messages)

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return runner.invoke(messages)
            except Exception as exc:  # noqa: BLE001 - provider raises many types
                last_error = exc
                if _is_safety_block(exc) or attempt == self.max_retries:
                    break
                delay = RETRY_BASE_DELAY * (2**attempt) + random.uniform(0, 0.4)
                logger.warning(
                    "Gemma call attempt %s/%s failed (%s); retrying in %.1fs",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                    delay,
                )
                time.sleep(delay)

        assert last_error is not None
        if _is_safety_block(last_error):
            raise GemmaError(
                "The AI couldn't look at that photo. Try a different one.",
                detail=str(last_error),
            ) from last_error
        raise GemmaError(detail=f"{type(last_error).__name__}: {last_error}") from last_error


# --------------------------------------------------------------- module level

_service: GemmaService | None = None


def get_gemma_service() -> GemmaService:
    """Shared service instance (FastAPI dependency-friendly)."""
    global _service
    if _service is None:
        _service = GemmaService()
    return _service


def reset_gemma_service() -> None:
    """Testing hook — drops the cached singleton."""
    global _service
    _service = None


# ------------------------------------------------------------------- helpers


def _build_messages(prompt: str, system: str | None) -> list[Any]:
    messages: list[Any] = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))
    return messages


def _with_json_instruction(messages: list[Any]) -> list[Any]:
    return messages + [
        HumanMessage(content="Respond with valid JSON only. No prose, no code fences."),
    ]


def _image_part(image_bytes: bytes, mime_type: str) -> _ImagePart:
    return _ImagePart(
        type="image_url",
        image_url=f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}",
    )


def _extract_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # list of content blocks
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in content
        )
    return str(content or "")


def _coerce(raw: Any, schema: type[T]) -> T:
    """Validate a model result against `schema`, tolerating stringified JSON."""
    if isinstance(raw, schema):
        return raw

    payload = raw
    if not isinstance(payload, (dict, list)):
        text = _extract_text(raw).strip()
        payload = _parse_json_text(text)

    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise SchemaValidationError(detail=str(exc)) from exc


def _schema_hint(schema: type[BaseModel]) -> str:
    """Render a Pydantic schema as an annotated JSON skeleton the model can copy."""
    import json

    def render(node: dict) -> str:
        if "enum" in node:
            return json.dumps(node["enum"])
        node_type = node.get("type", "string")
        if node_type == "object":
            fields = node.get("properties", {})
            required = set(node.get("required", fields))
            body = ",\n".join(
                f'  "{name}": {render(sub)}' + ("" if name in required else "  // optional")
                for name, sub in fields.items()
            )
            return "{\n" + body + "\n}"
        if node_type == "array":
            items = node.get("items", {"type": "string"})
            return f"[{render(items)}]"
        if node_type == "integer":
            return "0"
        if node_type == "number":
            return "0.0"
        if node_type == "boolean":
            return "true"
        return '"..."'

    return render(schema.model_json_schema())


def _parse_json_text(text: str) -> Any:
    import json

    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        candidate = candidate.split("\n", 1)[-1] if "\n" in candidate else candidate
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(detail=f"Invalid JSON from model: {text[:200]}") from exc


def _is_safety_block(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _SAFETY_MARKERS)
