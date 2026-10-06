"""Application-level errors.

`GemmaError` always carries a message that is safe to show to a user; internal
detail (stack traces, provider payloads) is logged, never returned.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "We couldn't evaluate your discovery right now. Your photo is saved. Try again."


class AppError(Exception):
    """Base error with an HTTP status and a user-safe message."""

    status_code = 500

    def __init__(self, message: str = FALLBACK_MESSAGE) -> None:
        super().__init__(message)
        self.message = message


class ImageValidationError(AppError):
    """Uploaded file is not an acceptable image."""

    status_code = 400


class InvalidIdentityError(AppError):
    """The supplied user identifier is not a valid UUID."""

    status_code = 400


class NotFoundError(AppError):
    """Requested resource does not exist."""

    status_code = 404


class GemmaError(AppError):
    """The model call failed, was blocked, or returned something unusable."""

    status_code = 502

    def __init__(self, message: str = FALLBACK_MESSAGE, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail
        if detail:
            logger.warning("Gemma call failed: %s", detail)


class MissingAPIKeyError(GemmaError):
    """No API key configured — a deployment problem, not a user problem."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__(
            "The AI service is not configured yet.", detail="GEMINI_API_KEY is not set"
        )


class SchemaValidationError(GemmaError):
    """Model returned JSON that did not satisfy the Pydantic schema."""

    def __init__(self, detail: str) -> None:
        super().__init__("Model returned an unexpected response. Please try again.", detail=detail)
