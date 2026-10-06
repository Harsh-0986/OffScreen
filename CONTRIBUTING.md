# Contributing

Thanks for looking at Offscreen. This is a hackathon project, so the bar is
"clear, tested, and explainable" rather than "exhaustive".

## Getting set up

```bash
git clone <your-fork>
cd outside-not-online

cp .env.example .env          # add GEMINI_API_KEY and SECRET_KEY

cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd frontend && pnpm install && pnpm dev
```

Before you start, read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Most
non-obvious decisions are explained there with the reasoning.

## The rules that matter

**1. Tests must stay offline.** No test may make a network call or touch the real
database. Stub the model; use the `db` fixture. The suite is fast and free because
of this, and it is the reason it can be run before every commit.

**2. Never trust model output.** Everything returned by Gemma is validated against
a Pydantic schema before it leaves the service. If you add a model call, add the
schema with it.

**3. Keep the API key server-side.** `GEMINI_API_KEY` must never appear in
anything under `frontend/`. The frontend's only configuration is
`NEXT_PUBLIC_API_BASE_URL`.

**4. Preserve the product principle.** The app exists to get people *out* of it.
When adding UI, ask whether it makes someone more likely to put the phone down. No
feeds, no notifications, no infinite scroll, no engagement loops.

## Workflow

```bash
# backend
uv run pytest
uv run ruff check app tests
uv run ruff format app tests

# frontend
pnpm lint
pnpm build
```

Commit messages should explain **why**, not what. The history is the best
documentation this project has — several commits record bugs and the reasoning
behind the fix, and that context is worth keeping.

## Adding a model call

1. Create or reuse a Pydantic schema in `app/schemas/ai.py`. Constrain the ranges.
2. Put the prompt in its own module under `app/prompts/`. Never inline a large
   prompt in a route.
3. Call it through `GemmaService` — never import the vendor SDK directly, or the
   graph stops being testable.
4. Add a test with a stubbed service. It must not hit the network.

## Adding an endpoint

1. Pydantic request/response schemas in `app/schemas/`.
2. The route in the matching module under `app/api/`, with the auth dependency.
3. Any SQL goes in `app/db/repositories.py` — routes should not build queries.
4. Tests for the happy path, the failure path, and that the response contains no
   stack trace.

## Style

**Backend** — `ruff format`, 100 character lines, type hints on public functions.
Docstrings explain *why* something is done, not what the line does.

**Frontend** — TypeScript, functional components, `'use client'` only where
needed. The design system lives in `globals.css`; use the existing tokens
(`bg-paper`, `text-ink`, `text-moss`) rather than inventing colours.

## What would be genuinely useful

- **Real photograph tests.** The single biggest gap. See
  [docs/TESTING.md](docs/TESTING.md) — the AI has never seen a real photo.
- **Calibration data.** Photos labelled with human scores would let us measure
  whether the evaluator agrees with people.
- **Frontend tests.** Currently only lint and build are enforced.

## Reporting bugs

Include what you expected, what happened, and how to reproduce it. If it involves
the model, include the exact response — model behaviour is hard to describe and
much easier to diagnose with the raw output.
