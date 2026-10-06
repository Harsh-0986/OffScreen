"""Prompt for the short reflection shown on the result screen (SPEC §5)."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You write the short reflection for "Outside, Not Online".

One or two sentences, warm and a little vivid. It should feel like a friend who went \
outside with you, not a grading machine. Never scold. Never mention the app, AI, \
models, scoring rubrics, or prompts.

Use "appears to be" style hedging for anything uncertain. Return JSON only.\
"""

USER_PROMPT_TEMPLATE = """\
The challenge was: "{prompt}"
The user photographed: {what_was_found}
The visual detail: {interesting_detail}
The evaluation summary: {reasoning_summary}
Score awarded: {score}/10
Completed: {completed}

Write a two-line reflection, plus a display title for the journal entry.

Return JSON with this exact shape:
{{
  "title": "journal entry title, max 5 words",
  "reflection": "1-2 sentences",
  "tagline": "a single short line, no more than 8 words"
}}\
"""


def build_user_prompt(evaluation: dict) -> str:
    return USER_PROMPT_TEMPLATE.format(
        prompt=evaluation.get("challenge_prompt", ""),
        what_was_found=evaluation.get("what_was_found", "something outside"),
        interesting_detail=evaluation.get("interesting_detail") or "—",
        reasoning_summary=evaluation.get("reasoning_summary", ""),
        score=evaluation.get("score", 0),
        completed=str(bool(evaluation.get("completed"))).lower(),
    )
