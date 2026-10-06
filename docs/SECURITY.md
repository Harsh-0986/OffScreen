# Security

What is protected, how, and what is deliberately not.

## The one rule that matters most

**`GEMINI_API_KEY` never reaches the browser.** The key lives only in the backend
process environment. The frontend has no code path that reads it, and the only
config it receives is `NEXT_PUBLIC_API_BASE_URL`.

## Accounts

The spec lists authentication as out of scope, but the data model is multi-user
and a shared laptop needs to tell two people apart, so the smallest workable
version was built:

- **Passwords**: PBKDF2-HMAC-SHA256, 600,000 rounds, random 16-byte salt per
  password. Standard library only, so there is no native dependency to break on
  deploy. Verification is constant-time.
- **Sessions**: stateless HMAC-SHA256 signed tokens, 30-day expiry. No session
  table, so there is nothing to clean up. Rotating `SECRET_KEY` logs everyone out.
- **Token integrity**: the user id is inside the signed body, so it cannot be
  edited. A tampered token fails the signature check and returns 401.
- **Account enumeration**: login returns one message — "Email or password is
  incorrect." — whether the email is unknown or the password is wrong. A test
  asserts both responses are identical.
- **Deleted accounts**: a token for a user that no longer exists is rejected
  rather than trusted.

### Known limits

This is a hackathon-grade auth layer, not a production one:

- No rate limiting on login, so passwords can be brute-forced
- No email verification, password reset, or account deletion
- No refresh tokens, so there is no revocation short of rotating `SECRET_KEY`
- Tokens cannot be individually revoked

Add all of these before this handles real users.

## Uploads

An uploaded file is treated as hostile:

| Threat | Defence |
| --- | --- |
| Executable renamed to `.jpg` | Type confirmed by **magic bytes**, not the client's content type |
| Denial of service via huge file | Size cap enforced **while streaming**, so the body is never fully buffered |
| Path traversal via filename | The client's filename is **discarded**; files are stored under a generated UUID |
| Overwritten files | UUID collision is not a practical concern |
| Model confusion from transparency | Alpha is flattened onto white before resizing |
| Excessive token cost | Longest edge capped at 1280px before the model sees it |

## Model output

**Nothing the model returns is trusted.**

- Every response is validated against a Pydantic schema before it leaves the
  service. Unknown fields are dropped; wrong types and out-of-range values are
  rejected.
- Scores are constrained to 0–10 and confidence to 0.0–1.0 by the schema, not by
  the prompt alone.
- Categories are constrained to a known set, and the deterministic category
  override is re-validated rather than patched in.
- Model-generated text is only ever rendered as text. It is never executed, and
  never interpolated into a query.

## Error handling

`AppError` subclasses carry an HTTP status and a **user-safe message**. A global
exception handler returns that message; stack traces and provider payloads stay in
the server logs. There are tests asserting no response contains `Traceback`.

Safety blocks, timeouts, rate limits, and invalid JSON all surface as a single
short `GemmaError` with copy a person can act on.

## Privacy

- Photographs are stored on local disk under `UPLOAD_DIR` and served as static
  files. They are **not public by default** — only the app can read them.
- The journal and profile endpoints are scoped to the authenticated user. Passing
  another user's `challenge_id` returns 404 and never reaches the model; there is a
  test asserting the model is not called in that case.
- Photographs are sent to the Google Gemini API for analysis. This is a hosted
  API, so the images leave the machine. Don't make stronger privacy claims than
  that without switching to local inference.

## Not implemented

Worth stating plainly rather than implying otherwise:

- HTTPS termination (assume a reverse proxy in production)
- CSRF protection — safe today because auth is a bearer header, not a cookie, but
  it would matter if cookies were introduced
- Rate limiting anywhere
- Audit logging
