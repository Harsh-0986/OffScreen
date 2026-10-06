"""Deterministic personalization (SPEC §17).

Simple, explainable, and measurable:

- with probability `PREFERENCE_WEIGHT` (0.6) the category is drawn from the
  categories the user actually enjoys, weighted by their accumulated weight
- otherwise it is drawn uniformly from every category, which is where the
  exploration comes from

Choosing the category up front also means the model is constrained rather than
asked to self-select, which makes the 60/40 split observable instead of a
suggestion buried in a prompt.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any

from app.constants import CHALLENGE_CATEGORIES, PREFERENCE_WEIGHT

# Enough history before a favourite is trusted as a favourite.
MIN_WEIGHT_FOR_FAVOURITE = 1.0


def daily_seed(user_id: str, day: str) -> int:
    """Stable seed per user per day, so `/today` is reproducible."""
    digest = hashlib.sha256(f"{user_id}:{day}".encode()).hexdigest()
    return int(digest[:12], 16)


def weighted_favorites(profile: dict[str, Any]) -> dict[str, float]:
    """Categories the user has a real signal for."""
    favorites = profile.get("favorite_categories") or {}
    if isinstance(favorites, list):  # tolerate a plain list of names
        favorites = {name: MIN_WEIGHT_FOR_FAVOURITE for name in favorites}
    return {
        category: float(weight)
        for category, weight in favorites.items()
        if category in CHALLENGE_CATEGORIES and float(weight) >= MIN_WEIGHT_FOR_FAVOURITE
    }


def select_category(
    profile: dict[str, Any],
    *,
    seed: int | None = None,
    preference_weight: float = PREFERENCE_WEIGHT,
) -> tuple[str, str]:
    """Return `(category, mode)` where mode is "familiar" or "exploration"."""
    rng = random.Random(seed)
    favorites = weighted_favorites(profile)

    if not favorites or rng.random() >= preference_weight:
        return rng.choice(sorted(CHALLENGE_CATEGORIES)), "exploration"

    names = sorted(favorites)
    weights = [favorites[name] for name in names]
    return rng.choices(names, weights=weights, k=1)[0], "familiar"


def describe_choice(profile: dict[str, Any], category: str, mode: str) -> str:
    """Human-readable note for the API response and the journal."""
    if mode == "familiar":
        return f"Picked {category} — one of your favourites."
    return f"Picked {category} — a step outside your usual categories."
