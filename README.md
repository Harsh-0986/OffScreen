# Outside, Not Online

> One photo. One discovery. One reason to go outside.

An AI-powered outdoor discovery journal. You get one small, interesting real-world
challenge. You leave the app, find something, photograph it, and come back. Gemma
looks at the photo, judges whether it satisfies the challenge, writes a short
reflection, and awards discovery points.

Built for the **Hacktoberfest 2026 Open-Source AI Challenge — "Touch Grass"**.

## How it works

```
Open app  →  Today's challenge  →  Close the app, go outside  →  Photograph
          →  Gemma looks  →  Score + reflection  →  Journal  →  Come back tomorrow
```

The design goal is that you leave the app. There is no feed, no streak pressure,
no notifications, and no infinite scroll.

## Repository layout

```
.
├── backend/          FastAPI · LangGraph · Gemma service · SQLite
│   ├── app/
│   │   ├── api/          challenges, photos, discoveries, journal, profile, auth
│   │   ├── graph/        LangGraph state, nodes, and both graphs
│   │   ├── prompts/      one module per prompt (SPEC §22)
│   │   ├── services/     gemma, images, auth, personalization, analysis
│   │   ├── models/       SQLAlchemy ORM models
│   │   ├── schemas/      Pydantic request/response + model-output schemas
│   │   ├── db/           engine, session, repositories
│   │   └── constants.py, config.py, errors.py
│   └── tests/           162 tests, all offline (no network, no model calls)
└── frontend/         Next.js 16 · Tailwind 4 · Framer Motion
    └── src/
        ├── app/          /  /login  /today  /mission  /submit  /result  /journal  /profile
        ├── components/   nav, states
        └── lib/          typed API client, auth context, types
```

## Quickstart

### 1. Configure

```bash
cp .env.example .env
```

Then edit `.env`:

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio key. **Server-side only — never sent to the browser.** |
| `SECRET_KEY` | Signs session tokens. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `GEMMA_MODEL` | Model id, default `gemma-4-26b-a4b-it` |
| `DISCOVERY_PIPELINE` | `combined` (default, one multimodal call) or `two_stage` |
| `DATABASE_URL` | SQLAlchemy URL; SQLite for the MVP |
| `SQLITE_JOURNAL_MODE` | `WAL` by default; the app continues if it cannot be set |
| `UPLOAD_DIR` | Where uploaded photographs are stored |
| `MAX_IMAGE_BYTES` | Upload cap, default 10 MB |
| `CORS_ORIGINS` | Comma-separated frontend origins |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend only; public config, no secrets |

### 2. Backend

```bash
cd backend
uv sync                                          # creates .venv and installs everything
uv run uvicorn app.main:app --reload --port 8000
```

Verify: <http://localhost:8000/health> → `{"status":"ok"}`
Verify the model: `curl -X POST localhost:8000/api/test/gemma`

### 3. Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open <http://localhost:3000>, create an account, and go outside.

## Tests

```bash
cd backend && uv run pytest                  # 162 tests, offline
cd backend && uv run ruff check app tests
cd frontend && pnpm lint && pnpm build
```

`uv sync` installs from `backend/pyproject.toml` and `backend/uv.lock`, including
the project itself, so `import app` works from any directory. `uv add <pkg>` and
`uv add --dev <pkg>` are the only supported way to change dependencies.

Every backend test runs against an in-memory SQLite database and a stubbed model,
so the suite makes no network calls and never touches your real database.

## Architecture notes

**Two LangGraph graphs, both linear** (SPEC §8):

```
challenge:  START → load_context → generate_challenge → END
discovery:  START → load_challenge → analyze_photo → evaluate_discovery
                   → generate_feedback → save_discovery → update_profile → END
```

The only branch is an error guard: a missing challenge short-circuits to `END` so
the model is never called against nothing.

**Structured output.** Gemma frequently ignores the provider's function-calling
schema and returns its own key names, so the default path renders the Pydantic
schema into the prompt as an annotated JSON skeleton, parses the reply, and
validates it. A failure earns exactly one self-repair attempt. Set
`GEMMA_STRUCTURED_OUTPUT_MODE=tooling` to use provider function calling instead.

**One multimodal call** for describe-and-judge (SPEC §43), because separate calls
cost more and let the model contradict its own description. `DISCOVERY_PIPELINE=two_stage`
restores the two-stage path for comparison.

**Deterministic personalization** (SPEC §17): the category is chosen before
generation — ~60% weighted from the user's favourites, ~40% uniform exploration,
seeded per user per day — and passed to the model as a hard constraint. The model
cannot override it. That makes the split measurable instead of aspirational.

**Security.** Passwords are PBKDF2-HMAC-SHA256 (stdlib, no native dependency).
Sessions are stateless HMAC tokens. Login returns one message whether the email is
unknown or the password is wrong, so it cannot enumerate accounts. Uploads are
checked by magic bytes rather than the client's content type, capped while
streaming, and stored under generated UUID filenames — the client's filename is
never used. Model output is never trusted: everything is validated by Pydantic
before it reaches a response, and errors return short user-facing messages with no
stack traces.

## Development status

| Phase | Scope | State |
| --- | --- | --- |
| 0 | Monorepo setup | done |
| 1 | Gemma connection | done, verified live |
| 2 | Challenge generator | done |
| 3 | Photo upload + analysis | done |
| 4 | Discovery evaluation | done |
| 5 | Database | done (pulled forward) |
| 6 | Journal | done |
| 7 | Personalization | done |
| 8 | Frontend + animations | done |
| 9 | **Real outdoor test** | **pending — see below** |
| 10 | Empty/loading/error states, demo data | states done; demo data pending real photos |

### What still needs a human

The fixed AI test cases from SPEC §41 — obvious success, obvious failure,
ambiguous, unrelated, poor quality — and the real outdoor run in SPEC §37 have not
been done. The model has never been shown a real photograph, so scoring quality is
unverified. Demo discoveries must use real photos, not seeded fakes.

## License

MIT
