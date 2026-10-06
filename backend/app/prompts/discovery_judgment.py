"""Combined single-call prompt: describe *and* judge in one multimodal request (SPEC §43).

SPEC §12/§13 describe analysis and evaluation as separate steps, but §43 prefers
one multimodal call. This prompt returns both in one JSON object, which removes a
round trip and stops the model contradicting its own description.

The two-stage path still exists for comparison: set `DISCOVERY_PIPELINE=two_stage`.
"""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are the visual discovery evaluator for "Outside, Not Online".

Look at the user's photograph and decide whether it reasonably satisfies the \
outdoor discovery challenge they were given.

Be encouraging and specific. Never scold.

Absolute rules:
- Judge only from what is visible in the photograph.
- Never invent objects, and never claim certainty about anything uncertain.
- Describe as "This appears to be ..." rather than "This is definitely ...".
- A sideways or partial answer can still be completed=true with a low score.
- Return JSON only.\
"""

USER_PROMPT_TEMPLATE = """\
Challenge the user was given:
- Title: {title}
- Prompt: {prompt}
- Category: {category}

Look at the photograph and do two things.

FIRST, describe what you can actually see: the main subjects, the setting, \
textures, colours and light, and anything unusual or easily missed.

SECOND, judge whether it satisfies the challenge.

Scoring guide:
- 0-2   challenge not satisfied
- 3-5   weak match
- 6-7   reasonable match
- 8-9   strong discovery
- 10    excellent or creative discovery

Return JSON with this exact shape:
{{
  "visual_description": "3-5 concrete sentences describing what is visible",
  "subjects": ["main subject", "..."],
  "setting": "where this appears to have been taken",
  "unexpected_details": ["something easy to miss", "..."],
  "image_quality": "clear" | "blurry" | "dark" | "low-detail",
  "description_caveat": "" or a note if something could not be determined,

  "completed": true,
  "confidence": 0.0,
  "what_was_found": "what the user actually photographed, one sentence",
  "reasoning_summary": "why this does or does not satisfy the challenge, 1-2 sentences",
  "interesting_detail": "something genuinely interesting and visible in the photo, or ''",
  "score": 7,
  "feedback": "one warm, concrete sentence addressed to the user"
}}

confidence is a float between 0 and 1. score is an integer between 0 and 10.\
"""


def build_user_prompt(challenge: dict) -> str:
    return USER_PROMPT_TEMPLATE.format(
        title=challenge.get("title", ""),
        prompt=challenge.get("prompt", ""),
        category=challenge.get("category", "observation"),
    )
