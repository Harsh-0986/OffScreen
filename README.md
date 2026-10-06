# Offscreen

> *A photo walk, one challenge at a time.*

**Outside, Not Online** — an AI-powered outdoor discovery journal built for the
**Hacktoberfest 2026 Open-Source AI Challenge: "Touch Grass"**.

You get one small, interesting real-world challenge. You leave the app, find
something, photograph it, and come back. Gemma looks at the photo, judges whether
it satisfies the challenge, writes a short reflection, and awards discovery points.

The design goal is that you leave the app. There is no feed, no streak pressure,
no notifications, and no infinite scroll.

```
Open app  →  Today's challenge  →  Close the app, go outside  →  Photograph
          →  Gemma looks  →  Score + reflection  →  Journal  →  Come back tomorrow
```

## Why it exists

People consume enormous amounts of digital content but increasingly experience
the world through screens. Offscreen gives people a reason to put the phone down
— and a reason to pick it back up that isn't a notification.

## Documentation

| Document | What's in it |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, both LangGraph graphs, state, and the decisions behind them |
| [docs/API.md](docs/API.md) | Every endpoint with request/response examples |
| [docs/TESTING.md](docs/TESTING.md) | Test strategy, how to run it, and the AI test cases that still need real photos |
| [docs/DEV_SUBMISSION.md](docs/DEV_SUBMISSION.md) | Draft write-up for the DEV submission, with the gaps marked |
| [docs/SECURITY.md](docs/SECURITY.md) | Threat model and what protects what |
| [SPEC.md](SPEC.md) | The original product and technical specification |

## Repository layout

```
.
├── backend/          FastAPI · LangGraph · Gemma service · SQLite
│   ├── app/
│   │   ├── api/          challenges, photos, discoveries, journal, profile, auth
│   │   ├── graph/        LangGraph state, nodes, and both graphs
│   │   ├── prompts/      one module per prompt
│   │   ├── services/     gemma, images, auth, personalization, analysis
│   │   ├── models/       SQLAlchemy ORM models
│   │   ├── schemas/      Pydantic request/response + model-output schemas
│   │   ├── db/           engine, session, repositories
│   │   └── constants.py, config.py, errors.py
│   └── tests/           169 tests, all offline
└── frontend/         Next.js 16 · Tailwind 4
    └── src/
        ├── app/          / · /login · /today · /mission · /submit · /result · /journal · /profile
        ├── components/   nav, states
        └── lib/          typed API client, auth context, image helper, types
```

## Quickstart

### 1. Configure

```bash
cp .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio key. **Server-side only — never sent to the browser.** |
| `SECRET_KEY` | Signs session tokens. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `GEMMA_MODEL` | Model id, default `gemma-4-26b-a4b-it` |
| `DISCOVERY_PIPELINE` | `combined` (default, one multimodal call) or `two_stage` |
| `GEMMA_STRUCTURED_OUTPUT_MODE` | `prompt` (default) or `tooling` |
| `DATABASE_URL` | SQLAlchemy URL; SQLite for the MVP |
| `UPLOAD_DIR` | Where uploaded photographs are stored |
| `MAX_IMAGE_BYTES` | Upload cap, default 10 MB |
| `CORS_ORIGINS` | Comma-separated frontend origins |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend only; public config, no secrets |

See [`.env.example`](.env.example) for the full list.

### 2. Backend

```bash
cd backend
uv sync                                          # creates .venv from uv.lock
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
cd backend && uv run pytest                  # 169 tests, offline
cd backend && uv run ruff check app tests
cd frontend && pnpm lint && pnpm build
```

Every backend test runs against an in-memory SQLite database and a stubbed model,
so the suite makes no network calls and never touches your real database. See
[docs/TESTING.md](docs/TESTING.md).

## Status

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
| 9 | **Real outdoor test** | **pending — see docs/TESTING.md** |
| 10 | Empty/loading/error states, demo data | states done; demo data pending real photos |

**What still needs a human:** the model has never been shown a real photograph, so
scoring quality is unverified. Demo discoveries must use real photos, not seeded
fakes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Tests must stay offline and stubbed; no
test may make a network call or touch the developer's real database.

## License

MIT
