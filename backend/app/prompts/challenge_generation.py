"""Prompts for generating the daily outdoor discovery challenge (SPEC §22)."""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """\
You generate outdoor discovery challenges for "Outside, Not Online", an app that \
gets people out of their screens and into the physical world.

Rules:
- The challenge must be answerable with a single photograph taken outside.
- It must be specific, curious, and slightly playful. Never generic.
- Never mention the app, phones, screens, or uploading.
- It must be doable in under 30 minutes on a normal walk.
- Never repeat a challenge the user has already seen.
- Return JSON only. No prose, no code fences.

Difficulty scale:
1 = almost impossible to fail
2 = easy, most people find something
3 = requires real looking
4 = requires patience or a detour

Categories: observation, nature, architecture, color, texture, animals, people, \
light, shapes, history, creativity.\
"""

USER_PROMPT_TEMPLATE = """\
Generate today's discovery challenge for {display_name}.

Today is {today}.

Their favourite categories: {favorite_categories}.
Categories they have explored: {explored_categories}.

Challenges they have already been given (do not repeat these or near-variants):
{recent_challenges}

Discoveries they have already made (use for flavour only):
{recent_discoveries}

{freshness_hint}

Return JSON with this exact shape:
{{
  "title": "short evocative name, max 5 words",
  "prompt": "the instruction the user reads, one or two short sentences",
  "category": "one category from the list",
  "difficulty": 1,
  "estimated_minutes": 20
}}\
"""


def build_user_prompt(context: dict[str, Any]) -> str:
    """Render the challenge prompt from the user's history.

    `context` mirrors the payload described in SPEC §10.
    """
    profile = context.get("user_profile") or {}
    recent_challenges = context.get("recent_challenges") or []
    recent_discoveries = context.get("recent_discoveries") or []

    if recent_challenges:
        freshness_hint = "Make this noticeably different in angle from the ones above."
    else:
        freshness_hint = "This is their first challenge — make it inviting and easy to win."

    return USER_PROMPT_TEMPLATE.format(
        display_name=profile.get("display_name") or "a curious human",
        today=context.get("today", "today"),
        favorite_categories=_join(profile.get("favorite_categories")),
        explored_categories=_join(profile.get("explored_categories")),
        recent_challenges=_bullets(recent_challenges) or "(none yet)",
        recent_discoveries=_bullets(recent_discoveries) or "(none yet)",
        freshness_hint=freshness_hint,
    )


def _bullets(items: list[Any]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _join(values: Any) -> str:
    if not values:
        return "none yet"
    if isinstance(values, dict):
        return ", ".join(f"{k} ({v})" for k, v in values.items())
    return ", ".join(str(v) for v in values)


__all__ = ["SYSTEM_PROMPT", "build_user_prompt", "json"]
