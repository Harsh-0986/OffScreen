# Architecture

How Offscreen is put together, and why each piece is shaped the way it is.

## The shape of the system

```
Next.js (frontend)  ──HTTP──>  FastAPI  ──>  LangGraph  ──┬──>  Gemma (Gemini API)
                                                   │
                                                   └──>  SQLite + local uploads
```

The frontend never talks to the model and never holds an API key. All model
access goes through the backend, which is the only place `GEMINI_API_KEY` exists.

## Two linear graphs

The whole agent is two LangGraph state graphs. Neither loops, neither decides
anything on its own, and both are short enough to read in one sitting.

**Challenge generation**

```
START → load_context → generate_challenge → END
```

`load_context` gathers the user's profile and recent activity. `generate_challenge`
picks a category, asks the model for a challenge, validates it, and regenerates
once if the title repeats.

**Discovery evaluation**

```
START → load_challenge → analyze_photo → evaluate_discovery
      → generate_feedback → save_discovery → update_profile → END
```

`load_challenge` fetches the challenge being answered. `analyze_photo` looks at
the photograph. `evaluate_discovery` judges it. `generate_feedback` writes the
reflection and journal title. `save_discovery` persists everything and closes out
the challenge. `update_profile` re-reads the profile so the client gets updated
totals in a single round trip.

### The one branch

There is exactly one conditional edge: if `load_challenge` fails, the graph jumps
straight to `END`.

```python
def _route_after_load(state):
    return "skip" if state.get("error") else "analyze_photo"
```

This exists because the original version kept calling the model after a failed
lookup — burning a paid vision call to judge a photograph against nothing. The
tests now assert the model is never invoked in that case.

## State

`app/graph/state.py` defines `DiscoveryState`, a `TypedDict` with
`total=False` so nodes return only what they change. Every value is
JSON-serializable.

One detail worth knowing: **raw image bytes are deliberately kept out of the
state.** They are bound into the node closure when the graph is built. Putting
them in state would make it unserializable, and the spec requires a serializable
state so a run can be logged or replayed.

## Getting usable JSON out of Gemma

This was the hardest part of the build, and the first live call exposed it.

Gemma frequently **ignores the provider's function-calling schema** and returns
its own key names — asked for `title`, it returned `challenge_title`. Using
`with_structured_output` alone produced objects that failed validation.

The default path (`GEMMA_STRUCTURED_OUTPUT_MODE=prompt`) instead:

1. Renders the Pydantic schema into the prompt as an annotated JSON skeleton,
   including enum values so the model sees the allowed categories.
2. Parses the reply, tolerating markdown code fences.
3. Validates against the schema — nothing leaves the service unvalidated.
4. On failure, allows **exactly one** self-repair attempt, showing the model its
   own validation error.

That repair loop earned its keep on the very first live run: the model returned
`category: "Exploration"`, failed validation, and corrected itself.

`GEMMA_STRUCTURED_OUTPUT_MODE=tooling` restores provider function calling for
models verified to honour the schema.

## One multimodal call, not four

The obvious pipeline is *identify → describe → evaluate → feedback*. That costs
four model calls and lets the model contradict its own description.

The default (`DISCOVERY_PIPELINE=combined`) sends **one** multimodal request that
returns the description and the evaluation together. `DISCOVERY_PIPELINE=two_stage`
restores the separate describe/judge path so the two can be compared during real
testing.

## Deterministic personalization

The spec asks for roughly 60% familiar categories and 40% exploration. Left to
the model that is a suggestion it may ignore and you cannot measure.

Instead the **category is chosen before generation**:

- with probability 0.6, drawn from the user's favourite categories weighted by
  accumulated weight
- otherwise drawn uniformly from all eleven categories

The choice is passed to the model as a hard constraint, and if the model returns
a different category the deterministic one wins — re-validated through the
schema, so an invalid category cannot slip in. The split is seeded per user per
day, so `/today` is stable across refreshes.

A test draws 2000 seeds and asserts familiar lands in 55–65%.

## Uploads

An uploaded file is treated as hostile:

- type is confirmed by **magic bytes**, not the client's content type
- the size cap is enforced **while streaming**, so an oversized body is never
  fully buffered
- the stored filename is a generated **UUID**; the client's filename is discarded
- transparency is flattened onto white, so PNG/WebP alpha doesn't confuse the model
- images are downscaled so the longest edge is 1280px before being sent

## Error handling

`AppError` and its subclasses carry an HTTP status and a **user-safe message**. A
global exception handler returns that message; stack traces stay in the logs.
The model layer raises a single `GemmaError` type for invalid JSON, timeouts, rate
limits, safety blocks, and empty responses, each mapped to a message a person can
act on.

The photograph is saved **before** the model runs, so a model failure never loses
the user's photo.

## Storage

SQLite through SQLAlchemy, four tables: `users`, `challenges`, `discoveries`,
`user_preferences`. Switching to PostgreSQL is a `DATABASE_URL` change; the
repositories use no SQLite-specific SQL.

Two SQLite-specific details worth knowing:

- `PRAGMA journal_mode` is **persistent database state** requiring an exclusive
  lock, so it is attempted once per process and a failure is swallowed. A second
  process (like `uvicorn --reload`) must not be able to stop the app booting.
- `busy_timeout` is set before any locking pragma so concurrent writers wait
  instead of erroring.

## Dependencies between layers

```
api/  →  graph/  →  prompts/, schemas/
             ↓
         services/  (gemma, images, auth, personalization)
             ↓
           db/       (repositories only)
```

Two rules keep this honest:

1. **Nodes never import the vendor SDK.** They receive a `GemmaService`, which is
   why the entire graph is testable without a network.
2. **SQL never leaves `db/repositories.py`.** Nodes receive repository functions as
   injected callables, which is what let the database be pulled forward into an
   earlier phase without touching the graph.
