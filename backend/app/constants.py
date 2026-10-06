"""Shared constants for the discovery loop."""

from __future__ import annotations

CHALLENGE_CATEGORIES: frozenset[str] = frozenset(
    {
        "observation",
        "nature",
        "architecture",
        "color",
        "texture",
        "animals",
        "people",
        "light",
        "shapes",
        "history",
        "creativity",
    }
)

# Spec §17: roughly 60% familiar preference, 40% exploration.
PREFERENCE_WEIGHT = 0.6

ALLOWED_IMAGE_MIME_TYPES: tuple[str, ...] = (
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
)
