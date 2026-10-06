"""LangGraph nodes (SPEC §24).

Nodes are plain functions that take the state and return a partial state update.
The model is always reached through `GemmaService`, never imported directly, so
the graph is testable without a network call.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from typing import Any

from app.prompts import challenge_generation, personalization
from app.schemas.ai import ChallengeDraft
from app.services.gemma import GemmaService, get_gemma_service

logger = logging.getLogger(__name__)

# Number of previous challenges/discoveries shown to the model.
HISTORY_WINDOW = 8


def load_context(
    state: dict[str, Any],
    *,
    load_profile: Callable[[str], dict[str, Any]] | None = None,
    load_history: Callable[[str], list[str]] | None = None,
    load_discoveries: Callable[[str], list[str]] | None = None,
    now: date | None = None,
) -> dict[str, Any]:
    """Gather the user's profile and recent activity for the prompt.

    The loaders are injected. Phase 5 wires them to SQLAlchemy; before that they
    default to "new user" so the graph runs standalone.
    """
    user_id = state.get("user_id", "")

    profile = (load_profile or _empty_profile)(user_id)
    challenge_history = (load_history or _no_history)(user_id)[-HISTORY_WINDOW:]
    discoveries = (load_discoveries or _no_history)(user_id)[-HISTORY_WINDOW:]

    return {
        "user_profile": profile,
        "challenge_history": challenge_history,
        "challenge_titles": challenge_history,
        "recent_discoveries": discoveries,
        "context_date": (now or date.today()).isoformat(),
    }


def generate_challenge(
    state: dict[str, Any],
    *,
    service: GemmaService | None = None,
) -> dict[str, Any]:
    """Ask Gemma for today's challenge and validate it.

    A duplicated or near-duplicate of a previous challenge is rejected and
    regenerated once (SPEC §35: two consecutive challenges must not be identical).
    """
    gemma = service or get_gemma_service()

    context = {
        "user_profile": state.get("user_profile", {}),
        "explored_categories": sorted(
            (state.get("user_profile", {}).get("favorite_categories") or {}).keys()
            if isinstance(state.get("user_profile", {}).get("favorite_categories"), dict)
            else (state.get("user_profile", {}).get("favorite_categories") or [])
        ),
        "recent_challenges": state.get("challenge_history", []),
        "recent_discoveries": state.get("recent_discoveries", []),
        "today": state.get("context_date") or date.today().isoformat(),
    }

    draft = gemma.generate_structured(
        challenge_generation.build_user_prompt(context),
        ChallengeDraft,
        system=challenge_generation.SYSTEM_PROMPT,
    )

    seen = [t.strip().lower() for t in state.get("challenge_history", []) if t]
    if draft.title.strip().lower() in seen:
        logger.info("Regenerating duplicate challenge title: %s", draft.title)
        context["recent_challenges"] = [*context["recent_challenges"], draft.title]
        draft = gemma.generate_structured(
            challenge_generation.build_user_prompt(context)
            + "\n\nThat challenge was already given. Produce a different one.",
            ChallengeDraft,
            system=challenge_generation.SYSTEM_PROMPT,
        )

    return {
        "current_challenge": {
            **draft.model_dump(),
            "personalization_note": personalization.describe_preferences(
                state.get("user_profile", {})
            ),
        }
    }


def _empty_profile(user_id: str) -> dict[str, Any]:
    return {
        "id": user_id,
        "display_name": "Curious human",
        "total_points": 0,
        "discoveries_count": 0,
        "current_streak": 0,
        "favorite_categories": {},
    }


def _no_history(user_id: str) -> list[str]:
    return []
