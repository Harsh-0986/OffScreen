# Outside, Not Online

> One photo. One discovery. One reason to go outside.

An AI-powered outdoor discovery journal. You get one small, interesting real-world
challenge. You leave the app, find something, photograph it, and come back. Gemma
looks at the photo, judges whether it satisfies the challenge, writes a short
reflection, and awards discovery points.

Built for the **Hacktoberfest 2026 Open-Source AI Challenge — "Touch Grass"**.

## Repository layout

```
.
├── backend/     FastAPI + LangGraph + Gemma service
├── frontend/    Next.js + Tailwind + Framer Motion
├── SPEC.md      Product and technical specification
└── .env.example
```

## Quickstart

### Backend

```bash
cd backend
uv venv && uv pip install -r requirements.txt      # or: python -m venv .venv && pip install -r requirements.txt
cp ../.env.example ../.env                        # then add your GEMINI_API_KEY
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/health> → `{"status":"ok"}`

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open <http://localhost:3000>.

## Configuration

All configuration lives in `.env` at the repo root (see `.env.example`).

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio key. **Server-side only — never sent to the browser.** |
| `GEMMA_MODEL` | Model id, defaults to `gemma-4-26b-a4b-it`. |
| `DATABASE_URL` | SQLAlchemy URL; SQLite for the MVP. |
| `UPLOAD_DIR` | Where uploaded photographs are stored. |
| `MAX_IMAGE_BYTES` | Upload size cap (default 10 MB). |

## Development status

Tracked phase by phase in the git history. See `SPEC.md` §28–§39 for the phase plan.

## License

MIT
