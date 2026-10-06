"""LangGraph nodes (SPEC §24).

Nodes are plain functions that take the state and return a partial state update.
The model is always reached through `GemmaService`, never imported directly, so
the graph is testable without a network call.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import date
from typing import Any

from app.prompts import (
    challenge_generation,
    discovery_evaluation,
    discovery_judgment,
    feedback,
    personalization,
    photo_analysis,
)
from app.schemas.ai import (
    ChallengeDraft,
    DiscoveryEvaluation,
    DiscoveryFeedback,
    DiscoveryJudgment,
    PhotoAnalysis,
)
from app.services.gemma import GemmaService, get_gemma_service

logger = logging.getLogger(__name__)

# Number of previous challenges/discoveries shown to the model.
HISTORY_WINDOW = 8

# "combined" (default): one multimodal call returns description + evaluation (SPEC §43).
# "two_stage": separate describe and judge calls, kept for comparison during testing.
DISCOVERY_PIPELINE = os.environ.get("DISCOVERY_PIPELINE", "combined")


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


# --------------------------------------------------------- discovery nodes


def load_challenge(
    state: dict[str, Any],
    *,
    load: Callable[[str, str], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Fetch the challenge being answered, scoped to the requesting user."""
    challenge_id = state.get("challenge_id", "")
    user_id = state.get("user_id", "")

    challenge = (load or _no_challenge)(user_id, challenge_id)
    if not challenge:
        return {"error": "That challenge could not be found."}
    return {"current_challenge": challenge}


def analyze_photo(
    state: dict[str, Any],
    *,
    service: GemmaService | None = None,
    pipeline: str | None = None,
) -> dict[str, Any]:
    """Describe (and in the combined pipeline, judge) the photograph."""
    gemma = service or get_gemma_service()
    mode = pipeline or DISCOVERY_PIPELINE
    challenge = state.get("current_challenge")

    if mode == "two_stage":
        analysis = gemma.generate_structured_from_image(
            photo_analysis.build_user_prompt(challenge),
            state["image_bytes"],
            state["image_mime_type"],
            PhotoAnalysis,
            system=photo_analysis.SYSTEM_PROMPT,
        )
        return {"image_analysis": analysis.model_dump()}

    judgment = gemma.generate_structured_from_image(
        discovery_judgment.build_user_prompt(challenge or {}),
        state["image_bytes"],
        state["image_mime_type"],
        DiscoveryJudgment,
        system=discovery_judgment.SYSTEM_PROMPT,
    )
    return _split_judgment(judgment)


def evaluate_discovery(
    state: dict[str, Any],
    *,
    service: GemmaService | None = None,
    pipeline: str | None = None,
) -> dict[str, Any]:
    """Judge the photo against the challenge.

    In the combined pipeline the judgement already arrived with `analyze_photo`,
    so this node only normalises it into `state["evaluation"]`.
    """
    mode = pipeline or DISCOVERY_PIPELINE
    if mode != "two_stage":
        return {}

    gemma = service or get_gemma_service()
    evaluation = gemma.generate_structured(
        discovery_evaluation.build_user_prompt(
            state.get("current_challenge") or {}, state.get("image_analysis") or {}
        ),
        DiscoveryEvaluation,
        system=discovery_evaluation.SYSTEM_PROMPT,
    )
    return {"evaluation": evaluation.model_dump()}


def generate_feedback(
    state: dict[str, Any],
    *,
    service: GemmaService | None = None,
) -> dict[str, Any]:
    """Write the short reflection and the journal title."""
    gemma = service or get_gemma_service()
    evaluation = dict(state.get("evaluation") or {})
    evaluation["challenge_prompt"] = (state.get("current_challenge") or {}).get("prompt", "")

    result = gemma.generate_structured(
        feedback.build_user_prompt(evaluation),
        DiscoveryFeedback,
        system=feedback.SYSTEM_PROMPT,
    )
    return {"feedback": result.model_dump()}


def save_discovery(
    state: dict[str, Any],
    *,
    save: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Persist the discovery and close out the challenge.

    Failed attempts are saved too, flagged `completed: false` — the journal shows
    the miss rather than hiding it.
    """
    evaluation = state.get("evaluation") or {}
    feedback_data = state.get("feedback") or {}
    challenge = state.get("current_challenge") or {}

    record = {
        "user_id": state.get("user_id", ""),
        "challenge_id": challenge.get("id", ""),
        "image_path": state.get("image_path", ""),
        "title": feedback_data.get("title") or evaluation.get("what_was_found") or "A discovery",
        "description": feedback_data.get("reflection", ""),
        "score": int(evaluation.get("score", 0)),
        "confidence": float(evaluation.get("confidence", 0.0)),
        "category": challenge.get("category", "observation"),
        "ai_feedback": evaluation.get("feedback", ""),
        "completed": bool(evaluation.get("completed", False)),
        "points_awarded": int(evaluation.get("score", 0)),
        "ai_reasoning": evaluation.get("reasoning_summary", ""),
        "interesting_detail": evaluation.get("interesting_detail", ""),
        "visual_description": (state.get("image_analysis") or {}).get(
            "visual_description", evaluation.get("visual_description", "")
        ),
        "tagline": feedback_data.get("tagline", ""),
        "minutes": challenge.get("estimated_minutes", 0),
    }

    saved = (save or _no_save)(**record)
    return {"discovery": saved}


def update_profile(
    state: dict[str, Any],
    *,
    refresh: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Re-read the profile so the client gets updated totals in one round trip."""
    return {"user_profile": (refresh or _empty_profile)(state.get("user_id", ""))}


def _split_judgment(judgment: DiscoveryJudgment) -> dict[str, Any]:
    """Separate the combined judgement into the two state keys the spec defines."""
    data = judgment.model_dump()
    # `visual_description` is the analysis node's field; the evaluation keeps
    # only its own judgement keys so the two never disagree.
    evaluation_keys = {
        "completed",
        "confidence",
        "what_was_found",
        "reasoning_summary",
        "interesting_detail",
        "score",
        "feedback",
    }
    return {
        "image_analysis": {k: v for k, v in data.items() if k not in evaluation_keys},
        "evaluation": {k: v for k, v in data.items() if k in evaluation_keys},
    }


def _no_challenge(user_id: str, challenge_id: str) -> dict[str, Any]:
    return {}


def _no_save(**record: Any) -> dict[str, Any]:
    return dict(record)


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
