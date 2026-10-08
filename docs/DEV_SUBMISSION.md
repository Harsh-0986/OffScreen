# Offscreen — submission post

> **Status: draft, not submitted.** Every `[BRACKETED]` item must be filled in by a
> human. The "What actually happened when I used it" section in particular
> **cannot be written by an agent** — those are real results from real
> photographs, and inventing them would be both dishonest and checkable.
>
> Post with tags `devchallenge`, `hf26challenge`. See
> [SUBMISSION_RUNBOOK.md](SUBMISSION_RUNBOOK.md) for the mechanics and the
> pre-publish checklist.

---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

**Offscreen** — *a photo walk, one challenge at a time.*

You open it and get one small, specific challenge: *"Find something that looks
like a face."* Then it tells you to close the app. You go outside, find the
thing, photograph it, come back, and Gemma looks at your photo, tells you what it
sees, and scores it. The journal remembers. Then it says come back tomorrow.

That's the whole product. There is no feed, no infinite scroll, no notifications,
no streak that punishes you for missing a day, and nothing to log in for. The
`/mission` screen has one sentence and one button, because the goal is that you
leave it.

I built it after noticing something uncomfortable about my own phone habits. Every
app on it is competing to give me a reason to stay inside it. I wanted to build
the opposite: an app whose success metric is you closing it.

**Who it's for:** anyone who has ever resolved to "go for a walk tomorrow" and
then spent the evening on the sofa. You do not need to be a photographer, a
hiker, or a birder. The challenges are small and specific — five to twenty
minutes on an ordinary walk.

## Demo

- Live: [DEPLOYED LINK — verify before submitting](https://offscreen-one.vercel.app/)
- Code: https://github.com/Harsh-0986/OffScreen
- [SCREENSHOT: today's challenge]
- [SCREENSHOT: mission mode — the screen with one button]
- [SCREENSHOT: a result, showing the score and Gemma's reflection]
- [SCREENSHOT: the journal]
- [VIDEO: a 2-minute screen recording of the full loop, if you have one — more
  reliable than a live link if the free-tier backend has spun down]

## Code

https://github.com/Harsh-0986/OffScreen

20 commits, built phase by phase from a written spec. FastAPI + LangGraph +
SQLite on the back, Next.js 16 + Tailwind on the front.

The bit I'm happiest with is the test suite: **169 tests, all hermetic.** No test
makes a network call, no test touches the real database, and the model is stubbed
everywhere. It runs in about eleven seconds and costs nothing, which meant I
could run it after every single change.

The commit history is also part of the documentation. Several commits are titled
"Fix X" and explain why the bug mattered — the journal images 404ing, the graph
quietly burning a paid model call on a failed lookup, an infinite React render
loop from an unstable object identity. That history is more useful than a
retrospective doc would have been.

## How I Built It

**Gemma 4** does all the thinking: it writes every challenge, judges every
photograph, and decides the score. Nothing works without it.

**LangGraph** orchestrates it as two deliberately boring, linear state graphs:

```
challenge:  START → load_context → generate_challenge → END

discovery:  START → load_challenge → analyze_photo → evaluate_discovery
                 → generate_feedback → save_discovery → update_profile → END
```

No autonomous loop, no planning, no self-reflection. Each node runs once. There
is exactly one branch — if the challenge can't be found, jump to `END`, because
there's no point paying for a vision call to judge a photograph against nothing.

Three decisions were made against the obvious implementation:

**1. One multimodal call, not four.** The textbook pipeline is identify →
describe → evaluate → feedback. That's four model calls and lets the model
contradict itself. Sending one request that returns the description and the
evaluation together is faster and more coherent. The two-stage path is still
there behind a flag so I could compare.

**2. Gemma ignores the function schema.** My first live call used the provider's
structured-output helper. Gemma ignored the JSON schema I'd declared and returned
its own key names — asked for `title`, it gave me `challenge_title`. So the
schema is now rendered into the prompt as an annotated JSON skeleton, the reply is
parsed and validated locally, and a validation failure buys the model exactly one
chance to fix itself. That repair loop earned its keep on its very first live run:
the model returned `category: "Exploration"`, failed validation, and corrected
itself. Nothing the model returns is trusted — all of it goes through Pydantic
before it reaches a response.

**3. Personalization you can measure.** "Favour what the user likes" left to the
model is a suggestion it may ignore, and you can't measure it. Instead the
category is chosen *before* generation — roughly 60% weighted toward the user's
favourites, 40% uniform exploration — and handed to the model as a hard
constraint it can't override. A test draws 2000 seeds and asserts the ratio. A
judges' score isn't a vibe; it's a number someone checked.

## Why Does Open Innovation Matter?

**[KEEP THIS SECTION HONEST — this is where most entries will overclaim.]**

The MVP runs against Google's hosted AI Studio API, so **photographs do leave my
laptop**. I'm not going to claim local inference or privacy properties I haven't
demonstrated. Here's what I can actually defend:

**It made the project possible at all.** A multimodal model I can call with an API
key, in an afternoon, for free at this scale — that's what turned "an idea about
putting the phone down" into a working thing I could iterate on over a week.
The interesting work went into prompt design, evaluation calibration, and agent
structure rather than into access. For a project whose entire premise is an AI
loop, that's the difference between shipping and not.

**It kept the model a choice rather than a dependency.** The model id is
configuration, not code. When generation was slow, the first thing I could do was
question whether I needed the big model for *writing challenges* at all — a task
that's mostly text generation and barely uses vision. Splitting the work between a
small model and the large one is now an obvious next step, and it's only obvious
because swapping models is one environment variable.

**LangGraph is the load-bearing piece of open infrastructure here.** The reason
this project's behaviour is explainable is that the orchestration is an open
source graph I can read, test, and inspect, rather than a black box that decides
what to call next. When the graph made a mistake — and it did, calling the model
after a failed lookup — I found it because the control flow was six lines long and
visible. The determinism is a property of choosing an open harness, not something
I wrote.

**And the exit exists.** Because the model is isolated behind one interface and
the weights are published, running it locally later is an implementation swap, not
a rewrite. I haven't done it, so I won't claim it, but the design doesn't close
that door.

## What actually happened when I used it

**[REQUIRED — author only. This is what the brief asks for and where writing is
judged most heavily. Do not let an agent fill this in.]**

- **Where and how many:** [e.g. "Three challenges over two evenings, on walks
  around my neighbourhood"]
- **Example 1** — Challenge: "[…]" · I photographed: "[…]" · Gemma scored: `[…]/10`
- **Example 2** — Challenge: "[…]" · I photographed: "[…]" · Gemma scored: `[…]/10`
- **Example 3** — Challenge: "[…]" · I photographed: "[…]" · Gemma scored: `[…]/10`

**What worked**

- [ ]

**What didn't**

- [ ]

**What surprised me**

- [ ]

This is the section I care about most, because the interesting failures are
usually more informative than the wins. My own suspicion, from the code and from
building it, is that the evaluator is probably **too generous** — if it hands
8–10 to anything vaguely plausible, the score stops meaning anything. If that
turned out to be true, the fix is a labelled test set of my own photographs with
scores I'd defend, and measuring the model against them. If instead it turned out
to be strict in the right way, I'd want to know that too.

## My Agent Session

[Optional, but this project is a good case for it: 20 commits built phase by
phase from a spec, with a human making the design calls.]

[SESSION LINK — save with `devrelay sessions submit` and embed with the
`agent_session` tag]

## Prize Categories

- **Overall** — entering this.
- **Best Use of Render** — the FastAPI backend and its Gemma calls run as a web
  service on Render, and the frontend is deployed on Vercel against it.

I'm not entering the other partner categories. Nothing in this project uses
Arduino, TabPFN, or Tinker, and a category is a claim that the technology did real
work — not a list of things I could have used.

---

## Thanks for participating!
