# Submission runbook

Operational handoff for submitting **Offscreen** to the DEV Hacktoberfest Week 1
challenge. Everything another agent needs is in this file and
[DEV_SUBMISSION.md](DEV_SUBMISSION.md). No prior context required.

## The target

| | |
| --- | --- |
| Challenge | Hacktoberfest Open-Source AI Challenge: Week 1 — "Touch Grass" |
| Page | https://dev.to/challenges/hacktoberfest-week1-2026-10-05 |
| Deadline | **October 11, 2026** |
| Required tags | `devchallenge`, `hf26challenge` |
| Top prize | $250 |
| Partner categories | $200 each (Render, TabPFN, Tinker, Arduino, and others) |

Judging criteria, in order of weight:

1. **Writing Quality** (weighted most heavily)
2. Relevance to the Prompt and Theme
3. Creativity
4. Technical Execution
5. Use of Partner Technology (optional)

The brief says: *"Bonus points if you take it outside, use it, and tell us how it
went."* The post must have a **real-world test section**. This is the single
biggest risk to the entry — see "Blockers" below.

## Who to post as

Already authenticated; do not re-authenticate.

| | |
| --- | --- |
| MLH identity | Harsh Shah |
| DEV username | `harsh2102` (id 4160967) |
| GitHub | `Harsh-0986` |
| Existing articles | **none** — this is the first post |

Verify before publishing:

```bash
devrelay --auth-status
devrelay articles me          # expect: []
```

## Repo

- URL: https://github.com/Harsh-0986/OffScreen
- Branch: `main`, ~20 commits, clean
- MIT licensed

## How to publish

### Preferred: MCP tools

A DevRelay MCP server is registered with pi (`~/.pi/agent/mcp.json`, user level):

```json
{
  "mcpServers": {
    "devrelay": {
      "command": "devrelay",
      "args": ["--stdio"],
      "exposure": "direct"
    }
  }
}
```

Tools are named `mcp__devrelay__<tool>`. The relevant ones:

| Tool | Purpose |
| --- | --- |
| `create_article` | Create the post. `published: false` saves a draft |
| `update_article` | Edit an existing post by id |
| `get_my_articles` | List your posts and their ids |
| `unpublish_article` | Unpublish by id |
| `submit_agent_session` | Save an agent session (the "My Agent Session" section) |

**`create_article` defaults to `published: false`** — a draft. A draft's `url` has
a `-temp-slug-<id>` suffix; the `edit_url` is the one to open for review.

Because `NEXT_PUBLIC_*` style disclosure is available, pass
`ai_disclosure_level: "some_ai"` unless the author rewrote the whole post
themselves.

Run `/reload` after changing `mcp.json`, or the tools will not appear in a running
session.

### Fallback: CLI through a shell

If MCP is unavailable, the same surface exists on the `devrelay` binary:

```bash
devrelay --auth-status
devrelay articles me
devrelay articles create      # see --help for flags
devrelay articles update
devrelay sessions submit
```

Note: `devrelay <cmd> --help` prints global help rather than per-command flags on
this version (0.1.18). Read the top-level `USAGE` block instead.

### The submission template

The challenge provides a prefilled draft. Decoded, the expected structure is:

```markdown
*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built
## Demo
## Code
## How I Built It
## Why Does Open Innovation Matter?
## My Agent Session
## Prize Categories
```

[DEV_SUBMISSION.md](DEV_SUBMISSION.md) follows exactly this order.

## Blockers — resolve before publishing

### 1. The deployed demo link does not work (verified)

At time of writing, the deployed frontend's JavaScript bundle contains the
hardcoded fallback:

```
$ # grep across deployed /_next chunks
http://localhost:8000      ← present
```

A visitor's browser therefore calls **their own** localhost, not the backend. Any
judge clicking through the demo gets a dead app.

Two parts to the fix:

```bash
# 1. Set the API URL where Vercel builds the frontend
#    Vercel → Project → Settings → Environment Variables
#    NEXT_PUBLIC_API_BASE_URL = https://<render-service>.onrender.com
#
# 2. Redeploy. This is required: NEXT_PUBLIC_* values are inlined at BUILD time,
#    so setting the variable without rebuilding changes nothing.
```

`NEXT_PUBLIC_API_BASE_URL` must be set in **Vercel**, not in the repo-root `.env` —
Next.js only reads env files from `frontend/`.

### 2. Render free tier loses data (verified behaviour, not yet checked on their service)

Render's free plan has an **ephemeral filesystem**, so:

- SQLite (`outside.db`) is wiped on every redeploy and restart
- `uploads/` photographs are wiped too, so journal images 404
- the service spins down after ~15 minutes idle, adding a cold start on top of a
  ~35s generation call

If the journal is empty for judges, say so in the post, or lead with a demo video
instead of a link. A persistent disk is the real fix (paid plan).

### 3. CORS must include the Vercel origin (likely not done)

The backend reads `CORS_ORIGINS` from `.env`, which currently lists only
`http://localhost:3000`. The deployed frontend's origin is
`https://offscreen-one.vercel.app`. Without it, browser requests are blocked even
after the API URL is corrected:

```
CORS_ORIGINS=http://localhost:3000,https://offscreen-one.vercel.app
```

### 4. The deployed build predates the rebrand

The live page still reads *"An outdoor discovery journal"* in the header rather
than the Offscreen wordmark. A redeploy picks up the current branding.

### 5. Missing: the real-world test content

**[REQUIRED — cannot be generated by an agent]**

The brief rewards *"take it outside, use it, and tell us how it went."* Writing
carries the most weight, and this section is where writing is judged. The post
draft has placeholders that only the author can fill:

- How many challenges were completed, and where
- For two or three: the challenge, what was photographed, and **the score awarded**
- **What the model got wrong** — over-generous scoring, wrong guesses, awkward
  feedback

Do not fabricate these. An entry that invents evaluation results is worse than an
entry that is honest about a thin test, and the numbers are checkable.

### 6. Agent session (optional, cheap, judges like it)

The brief says *"Save your session with DevRelay and embed it."* This project was
built almost entirely by an agent against a written spec, so the session is
genuinely long and worth including:

```bash
devrelay sessions submit          # or mcp__devrelay__submit_agent_session
```

Embed the result with the `agent_session` tag, or link to it.

## Prize categories

Pick deliberately and honestly. The categories are for *using that technology*,
not for mentioning it.

- **Overall ($250)** — the default; enter this.
- **Best Use of Render** — the backend genuinely runs on Render as its AI
  runtime and API host. This is the most defensible partner category, provided
  the deployment actually works when a judge clicks it (see Blocker 1).
- Do **not** claim Arduino, TabPFN, Tinker, or the others. None are used.

## Pre-publish checklist

- [ ] Frontend bundle no longer contains `localhost:8000`
- [ ] `GET <render-url>/health` returns `{"status":"ok"}`
- [ ] Register + login + challenge + upload works end to end from the deployed URL
- [ ] A journal image actually renders on the deployed site
- [ ] Real-world test section filled in with real results
- [ ] Post has tags `devchallenge` and `hf26challenge`
- [ ] Opens with the challenge attribution line
- [ ] Repo link resolves publicly
- [ ] No secrets in the post or the repo (`.env` is git-ignored; verify with `git ls-files | grep -i env`)
- [ ] Read the post back as a judge would, before publishing

## Rollback

`devrelay articles unpublish <id>` (or `mcp__devrelay__unpublish_article`) takes it
down. Editing after publishing is `update_article`. Do not delete and repost if a
fix is enough — the URL matters.

## Verified facts for the post

These were confirmed during the build and are safe to state:

- 20 commits, FastAPI + LangGraph + SQLite backend, Next.js 16 frontend
- 169 backend tests, all offline and hermetic (no network, no real database)
- Two linear LangGraph graphs; one conditional edge, as an error guard
- Challenge generation takes ~35s on the free Gemini tier; the frontend
  pre-generates the next day's challenge while the user is idle
- Uploads are validated by magic bytes, capped while streaming, and stored under
  generated UUID filenames
- Personalization is deterministic: ~60% weighted favourite categories, ~40%
  exploration, measured by a test over 2000 seeds

## Claims to avoid

The project runs against Google's hosted AI Studio API. Do **not** claim local
inference, offline operation, or privacy properties — none have been demonstrated.
The honest version of the "why open" argument is accessibility, configurability,
and not being locked in because the weights are published. Saying so plainly is
stronger writing than overclaiming.
