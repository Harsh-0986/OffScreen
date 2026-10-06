"""Prompt for describing what is visible in a user's photograph (SPEC §12)."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """\
You are the visual analyst for "Outside, Not Online".

Describe only what you can actually see in the photograph. Do not invent objects. \
Do not guess at things that are not visible.

Critical honesty rule (SPEC §14): never state a fact that cannot be inferred from \
the image. Say "This appears to be a mature tree", never "This tree is 80 years old". \
If you are unsure what something is, use "This appears to be" or "this may be".

Return JSON only.\
"""

USER_PROMPT_TEMPLATE = """\
Analyze this photograph.

{challenge_block}

Describe:
- the main subject(s) in the frame
- textures, colours, and light
- anything unusual, hidden, or easily missed
- the setting (street, park, garden, indoors by mistake, ...)

Return JSON with this exact shape:
{{
  "visual_description": "3-5 sentences describing what is visible, concretely",
  "subjects": ["main subject", "..."],
  "setting": "where this appears to have been taken",
  "unexpected_details": ["something easy to miss", "..."],
  "image_quality": "clear" | "blurry" | "dark" | "low-detail",
  "description_caveat": "" or a note if something could not be determined
}}\
"""


def build_user_prompt(challenge: dict[str, Any] | None = None) -> str:
    if challenge:
        challenge_block = (
            f"The user was trying to satisfy this challenge:\n"
            f"- {challenge.get('prompt', challenge.get('title', ''))}\n"
            f"Describe the photograph; do not evaluate the challenge yet."
        )
    else:
        challenge_block = "No challenge context was provided."
    return USER_PROMPT_TEMPLATE.format(challenge_block=challenge_block)
