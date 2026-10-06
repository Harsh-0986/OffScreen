"""Serializable state passed between LangGraph nodes (SPEC §9)."""

from __future__ import annotations

from typing import Any, TypedDict


class DiscoveryState(TypedDict, total=False):
    """State for both graphs.

    Every value must be JSON-serializable so a run can be logged or replayed.
    """

    user_id: str

    current_challenge: dict[str, Any]
    challenge_history: list[str]
    challenge_titles: list[str]
    recent_discoveries: list[str]
    context_date: str

    challenge_id: str

    image_path: str
    image_mime_type: str

    image_analysis: dict[str, Any]
    evaluation: dict[str, Any]
    feedback: dict[str, Any]

    user_profile: dict[str, Any]
    discovery: dict[str, Any]

    error: str
