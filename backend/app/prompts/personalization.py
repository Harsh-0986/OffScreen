"""Prompt fragments describing the user's discovered taste (SPEC §17)."""

from __future__ import annotations

from typing import Any

FAVOUR_PHRASE = "60% familiar preference, 40% exploration."


def describe_preferences(profile: dict[str, Any]) -> str:
    """Render favourite categories into a short natural-language summary."""
    favorites = profile.get("favorite_categories") or {}
    if isinstance(favorites, list):
        favorites = {name: 1 for name in favorites}

    ranked = sorted(favorites.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked:
        return "This user has no history yet. Pick something inviting and easy to win."

    top = ", ".join(f"{name} ({count})" for name, count in ranked[:3])
    return (
        f"This user enjoys {top}. "
        "Favour the categories they gravitate to, but keep variety — aim for "
        f"roughly {FAVOUR_PHRASE}"
    )


def build_context_block(profile: dict[str, Any]) -> str:
    """Full context block embedded in the challenge generation prompt."""
    return (
        f"User name: {profile.get('display_name') or 'a curious human'}\n"
        f"Total discoveries: {profile.get('discoveries_count', 0)}\n"
        f"Discovery points: {profile.get('total_points', 0)}\n"
        f"Current streak: {profile.get('current_streak', 0)}\n"
        f"{describe_preferences(profile)}"
    )
