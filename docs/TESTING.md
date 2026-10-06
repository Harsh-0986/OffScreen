# Testing

## Running the suite

```bash
cd backend && uv run pytest                  # 169 tests
cd backend && uv run ruff check app tests
cd frontend && pnpm lint && pnpm build
```

**Every backend test runs offline.** The model is stubbed, the database is an
in-memory SQLite instance, and no test makes a network call or touches the real
`outside.db`. That means the suite is fast, free, and safe to run at any time.

## How it stays offline

| Fixture | What it does |
| --- | --- |
| `fresh_database` | Autouse. Rebuilds the engine on a fresh in-memory database before every test |
| `db` | A session against that database |
| `override_db` | Points HTTP requests at the in-memory database |
| `make_user` | Creates an account and returns `(user, headers)` with a valid bearer token |

The in-memory engine uses a `StaticPool` deliberately. Without it SQLAlchemy opens
one connection per thread for in-memory SQLite, and `TestClient` runs the app on a
different thread than the test — so the two would see *separate databases* and
ownership tests would quietly pass against an empty one.

## What is covered

**Challenge generation** — prompt contents, history limits, duplicate-title
regeneration, error capture, and that two consecutive challenges never match.

**Personalization** — the 60/40 split measured over 2000 seeds, weighted
favourites, exploration reaching unfamiliar categories, per-day seeding stability.

**Images** — magic-byte detection, spoofed extensions, corrupt data, size caps,
aspect ratio, alpha flattening, and that stored filenames never contain client
input.

**Evaluation** — that the combined pipeline makes exactly one multimodal call, that
graph state stays serializable, that a missing challenge never reaches the model,
and that a failed discovery is still saved.

**Persistence** — profile updates, category preference accumulation, cascade
deletes, and that data survives a new session.

**Security** — forged and tampered tokens, another user's challenge, ownership
isolation, and that no response ever contains a stack trace.

**SQLite pragmas** — including connecting while another process holds an exclusive
lock, which is the failure that took the app down once.

## Bugs these tests caught

Worth recording, because several would have been invisible in a demo:

| Bug | Why it mattered |
| --- | --- |
| The graph called Gemma after a failed challenge lookup | Burned a paid vision call judging a photo against nothing |
| `getSnapshot` returned a fresh object each call | `useSyncExternalStore` compares by reference — an infinite render loop |
| In-memory SQLite used per-thread connections | The test and the API saw different databases |
| Preferences were only recorded when a user row existed | Silently dropped a category signal |
| Journal and submit disagreed on the image URL | Every journal image 404'd |
| An invalid category override raised a raw `ValidationError` | Would have surfaced as an unhandled 500 |
| Aborting between headers and body escaped the guard | Unhandled rejections in the console |

---

# The AI tests that are not written yet

**This is the most important gap in the project.**

Every model interaction so far has been either text-only (verified live) or
stubbed. **The model has never been shown a real photograph**, so scoring quality,
hedging behaviour, and calibration are all unverified.

The spec calls for fixed cases covering obvious success, obvious failure,
ambiguous, unrelated, and poor-quality images. Run them by hand:

| Case | Setup | Expect |
| --- | --- | --- |
| **Obvious success** | Challenge "Find something red." + a red flower | `completed: true`, score 7–10 |
| **Obvious failure** | Challenge "Find something red." + a grey pavement | `completed: false`, score 0–3 |
| **Ambiguous** | Challenge "Find symmetry." + a building with regular windows | `completed: true`, mid score, hedged wording |
| **Unrelated** | Challenge "Find an animal." + a photo of a car | `completed: false`, low score |
| **Poor quality** | Any challenge + a dark, blurred photo | `completed: false`, `image_quality` flags it |
| **Honesty** | Any photo of a plant or bird | Text hedges with "appears to be", never a hard species claim |

### Scripted manual pass

1. `uv run uvicorn app.main:app --reload --port 8000`
2. `curl -X POST localhost:8000/api/test/gemma` → confirm `success: true`
3. Front end: create an account, complete a challenge, upload each test photo
4. Record the actual `score`, `confidence`, `completed`, and `feedback` for each
5. Note anything where the model invents an object that isn't in the frame

### What to watch for

- **Over-generous scoring.** If everything lands 8–10, the evaluator isn't
  discriminating and the scoring means nothing.
- **Hedging drift.** The spec requires "this appears to be", not "this is
  definitely". Check the honesty rule actually holds.
- **Contradictions.** If the description and the judgement disagree, the
  `two_stage` pipeline is worth comparing.
- **`completed: false` on a good photo** — the failure mode users would notice
  most.

## Performance

Targets from the spec, and what was actually measured:

| Operation | Target | Observed |
| --- | --- | --- |
| Challenge generation | < 10s | ~35s (free tier) |
| Photo analysis | < 15s | not yet measured |
| Ordinary API response | < 500ms | met; only reads the database |

Challenge generation runs on the slow path by design — the frontend pre-generates
tomorrow's challenge while the user is idle, so the wait lands once, quietly.

## Writing new tests

- Never make a network call. Stub the model.
- Never touch the real database. Use the `db` fixture.
- Assert on behaviour, not implementation details.
- If a change makes SQLite pragmas or abort handling relevant, cover it — those
  two caused real outages.
