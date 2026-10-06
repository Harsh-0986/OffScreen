"""Photo analysis orchestration.

Keeps the endpoint thin: validate, ask the model, return. Scoring is Phase 4.
"""

from __future__ import annotations

import logging
from typing import Any

from app.prompts import photo_analysis
from app.schemas.ai import PhotoAnalysis
from app.services.gemma import GemmaService

logger = logging.getLogger(__name__)


def analyze_photo(
    service: GemmaService,
    *,
    image_bytes: bytes,
    mime_type: str,
    challenge: dict[str, Any] | None = None,
) -> PhotoAnalysis:
    """One multimodal call describing what is visible in the photograph."""
    prompt = photo_analysis.build_user_prompt(challenge)
    return service.generate_structured_from_image(
        prompt,
        image_bytes,
        mime_type,
        PhotoAnalysis,
        system=photo_analysis.SYSTEM_PROMPT,
    )
