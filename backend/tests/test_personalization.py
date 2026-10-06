"""Tests for deterministic personalization (SPEC §17, §35)."""

from __future__ import annotations

from collections import Counter

from app.constants import CHALLENGE_CATEGORIES
from app.services.personalization import (
    daily_seed,
    describe_choice,
    select_category,
    weighted_favorites,
)

PROFILE_NATURE = {
    "favorite_categories": {"nature": 7.0, "color": 4.0, "texture": 1.0},
}


def test_no_history_means_exploration() -> None:
    for seed in range(50):
        category, mode = select_category({}, seed=seed)
        assert mode == "exploration"
        assert category in CHALLENGE_CATEGORIES


def test_favorites_are_weighted_not_uniform() -> None:
    """nature (weight 7) should appear more than texture (weight 1)."""
    counts = Counter(select_category(PROFILE_NATURE, seed=s)[0] for s in range(600))
    assert counts["nature"] > counts["texture"]
    assert counts["texture"] > 0


def test_split_is_roughly_sixty_forty() -> None:
    """SPEC §17 asks for about 60% familiar, 40% exploration."""
    modes = Counter(select_category(PROFILE_NATURE, seed=s)[1] for s in range(2000))
    familiar = modes["familiar"] / 2000
    assert 0.55 < familiar < 0.65, modes


def test_exploration_eventually_reaches_new_categories() -> None:
    seen = {select_category(PROFILE_NATURE, seed=s)[0] for s in range(400)}
    assert len(seen - {"nature", "color", "texture"}) > 0, "must not only show favourites"


def test_weight_below_threshold_is_not_a_favourite() -> None:
    profile = {"favorite_categories": {"nature": 0.4}}
    for seed in range(200):
        assert select_category(profile, seed=seed)[1] == "exploration"


def test_unknown_categories_are_ignored() -> None:
    profile = {"favorite_categories": {"not_a_category": 9.0, "nature": 3.0}}
    assert set(weighted_favorites(profile)) == {"nature"}


def test_list_form_of_favorites_is_tolerated() -> None:
    assert set(weighted_favorites({"favorite_categories": ["nature", "color"]})) == {
        "nature",
        "color",
    }


def test_preference_weight_is_configurable() -> None:
    always_explore = Counter(
        select_category(PROFILE_NATURE, seed=s, preference_weight=0.0)[1] for s in range(50)
    )
    assert always_explore["exploration"] == 50


def test_same_seed_gives_same_category() -> None:
    """Determinism: /today must not change category on refresh."""
    first = select_category(PROFILE_NATURE, seed=daily_seed("u1", "2026-10-06"))
    second = select_category(PROFILE_NATURE, seed=daily_seed("u1", "2026-10-06"))
    assert first == second


def test_different_users_get_different_seeds() -> None:
    seeds = {daily_seed(uid, "2026-10-06") for uid in ["u1", "u2", "u3"]}
    assert len(seeds) == 3


def test_different_days_get_different_seeds() -> None:
    assert daily_seed("u1", "2026-10-06") != daily_seed("u1", "2026-10-07")


def test_describe_choice_is_human_readable() -> None:
    assert "nature" in describe_choice(PROFILE_NATURE, "nature", "familiar")
    assert "usual" in describe_choice(PROFILE_NATURE, "shapes", "exploration")
