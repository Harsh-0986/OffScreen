# API

Base URL in development: `http://localhost:8000`

Interactive docs: <http://localhost:8000/docs>

## Authentication

Every endpoint except `/health`, `/api/test/gemma`, and the two auth calls
requires a bearer token:

```
Authorization: Bearer <token>
```

Tokens are stateless HMAC-signed strings valid for 30 days. A request with a
missing, malformed, expired, or tampered token gets `401` with a short message
and no stack trace.

```bash
# Create an account
curl -X POST localhost:8000/api/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"outdoors123","display_name":"You"}'
# → {"token":"...","user":{"id":"...","email":"you@example.com","display_name":"You"}}

export TOKEN="<token>"

# Who am I
curl localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
```

Login deliberately returns **one message** whether the email is unknown or the
password is wrong, so the endpoint cannot be used to discover which addresses are
registered.

---

## System

### `GET /health`

```json
{ "status": "ok" }
```

### `POST /api/test/gemma`

Diagnostics. Makes two live model calls — free text, then structured JSON — so you
can confirm the connection without touching the product flows.

```bash
curl -X POST localhost:8000/api/test/gemma
```

```json
{
  "success": true,
  "model": "gemma-4-26b-a4b-it",
  "sample": "Take a deep breath and enjoy the fresh air.",
  "structured_ok": true,
  "error": null
}
```

Returns `200` even on failure, with `success: false` and a plain-language `error`,
so it can be used as a setup checklist. Expect **~35 seconds** on a free tier.

---

## Challenges

### `GET /api/challenges/today`

Returns the current challenge, generating and storing one on first request of the
day. Safe to call on every page load: the stored challenge is reused within a
24-hour window.

```json
{
  "challenge": {
    "id": "3f2a...",
    "title": "Hidden Faces",
    "prompt": "Find something that looks like a face.",
    "category": "nature",
    "difficulty": 2,
    "estimated_minutes": 20
  },
  "personalization_note": "Picked nature — one of your favourites."
}
```

### `POST /api/challenges/generate`

Same response. Optional body:

```json
{ "force_new": true }
```

`force_new` bypasses the reuse window and generates a fresh challenge. Omitting
the body, or sending an empty one, behaves like `/today`.

> Generation takes ~35s. The frontend pre-generates tomorrow's challenge while the
> user is idle so the morning wait is short.

---

## Photo analysis

### `POST /api/photos/analyze`

`multipart/form-data`:

| Field | Type | Required |
| --- | --- | --- |
| `image` | JPEG, PNG, or WebP | yes |
| `challenge_id` | uuid | no |
| `save` | bool | no |

Validates and describes the photograph. **Returns no score** — scoring happens in
the discovery flow below.

```json
{
  "visual_description": "A mossy wall beside a narrow path.",
  "subjects": ["moss", "wall"],
  "setting": "a park",
  "unexpected_details": ["a beetle"],
  "image_quality": "clear",
  "description_caveat": "",
  "width": 1280,
  "height": 960,
  "original_bytes": 2411004,
  "resized": true
}
```

---

## Discoveries

### `POST /api/discoveries`

The main event. `multipart/form-data` with `image` and `challenge_id`.

Validates the upload, stores the photograph, runs the discovery graph, scores the
result, and updates the profile — all in one call.

```json
{
  "discovery": {
    "id": "9b1e...",
    "challenge_id": "3f2a...",
    "image_url": "/uploads/6038d979-....jpg",
    "title": "A Face In The Branches",
    "description": "The branches create a surprisingly convincing facial outline.",
    "score": 9,
    "confidence": 0.91,
    "category": "nature",
    "completed": true,
    "feedback": "You found it. The branches really do resemble a face.",
    "reasoning": "The branches outline two eyes and a mouth.",
    "interesting_detail": "This appears to be a mature tree.",
    "visual_description": "Tree branches against a pale sky.",
    "points_awarded": 9,
    "tagline": "a face, hiding",
    "created_at": "2026-10-06T19:42:11.204918+00:00"
  },
  "profile": {
    "id": "...",
    "email": "you@example.com",
    "display_name": "You",
    "total_points": 9,
    "discoveries_count": 1,
    "current_streak": 1,
    "favorite_categories": { "nature": 1.0 }
  }
}
```

Notes:

- **`completed` can be `false`.** A photograph that doesn't satisfy the challenge
  is still saved, and still appears in the journal. Hiding misses would feel
  dishonest.
- `score` is 0–10; `confidence` is 0.0–1.0. Both are validated server-side.
- The photograph is saved **before** the model runs, so a model failure never
  loses it.

### `GET /api/journal`

Newest first. Query params: `limit` (max 100, default 50), `offset`.

```json
{ "discoveries": [ /* same shape as above */ ], "total": 2 }
```

Empty for a new account: `{ "discoveries": [], "total": 0 }`.

### `GET /api/profile`

```json
{
  "id": "...",
  "email": "you@example.com",
  "display_name": "You",
  "total_points": 83,
  "discoveries_count": 5,
  "current_streak": 4,
  "completed_challenges": 5,
  "outdoor_minutes_estimate": 95,
  "favorite_categories": { "nature": 3.0, "color": 1.0, "texture": 1.0 }
}
```

### `PATCH /api/profile`

```json
{ "display_name": "Harsh" }
```

`display_name` is required, 1–80 characters.

---

## Uploaded images

`GET /uploads/<uuid>.jpg`

Served as static files from `UPLOAD_DIR`. `image_url` in every response is
root-relative and always begins with `/` — the frontend joins it to the API base
with a guaranteed separator.

---

## Errors

Every error returns a short, human-readable message. Stack traces are never
returned.

```json
{ "detail": "That photo is too large. Keep it under 10 MB." }
```

| Status | Meaning |
| --- | --- |
| `400` | Invalid upload, unsupported type, or malformed user id |
| `401` | Missing, expired, or invalid session token |
| `404` | Challenge not found, or not yours |
| `409` | Email already registered |
| `422` | Request body failed validation |
| `502` | The model failed, timed out, was blocked, or returned unusable JSON |
| `503` | The AI service is not configured |
