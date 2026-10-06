"""Prompt for judging whether a photograph satisfies the challenge (SPEC §13)."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are the discovery evaluator for "Outside, Not Online".

Decide whether the user's photograph reasonably satisfies the given outdoor \
discovery challenge.

Be encouraging and specific, never mean.

Absolute rules:
- Judge only from what is visible in the photograph.
- Never invent objects, and never claim certainty about anything uncertain.
- Use "This appears to be ..." instead of "This is definitely ...".
- Be strict but fair: a partial or sideways answer can still be completed=true \
  with a low score and honest feedback.
- Return JSON only.\
"""

USER_PROMPT_TEMPLATE = """\
Challenge the user was given:
- Title: {title}
- Prompt: {prompt}
- Category: {category}

What the photo shows (from the visual analysis step):
{analysis}

Judge the discovery.

Scoring guide:
- 0-2   challenge not satisfied
- 3-5   weak match
- 6-7   reasonable match
- 8-9   strong discovery
- 10    excellent or creative discovery

Return JSON with this exact shape:
{{
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


def build_user_prompt(challenge: dict, analysis: dict) -> str:
    return USER_PROMPT_TEMPLATE.format(
        title=challenge.get("title", ""),
        prompt=challenge.get("prompt", ""),
        category=challenge.get("category", "observation"),
        analysis=_format_analysis(analysis),
    )


def _format_analysis(analysis: dict) -> str:
    lines = []
    if analysis.get("visual_description"):
        lines.append(f"Description: {analysis['visual_description']}")
    if analysis.get("subjects"):
        lines.append(f"Subjects: {', '.join(analysis['subjects'])}")
    if analysis.get("setting"):
        lines.append(f"Setting: {analysis['setting']}")
    if analysis.get("unexpected_details"):
        lines.append(f"Easy to miss: {'; '.join(analysis['unexpected_details'])}")
    return "\n".join(lines) or "No analysis available."
