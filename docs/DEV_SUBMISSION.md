*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

I built **Offscreen** — an AI-powered outdoor discovery journal.

The idea is simple: instead of giving people another reason to stay on their phones, the app gives them a reason to put their phones down.

Every session starts with a small outdoor challenge:

> Capture the shadow of a person walking past you.

Or:

> Spot a piece of faded, hand-painted advertising that has almost vanished into a building's walls.

The challenge might take five minutes or twenty-five.

Then comes the important part:

**Put the phone down. Go outside.**

When you come back, you bring a photograph of what you discovered. Gemma looks at the photograph, interprets what you found, and scores the discovery.

The app deliberately has **no timer, no feed, and nothing to scroll**. The shortest part of the experience is supposed to be the time spent in the app.

The goal isn't to make people spend more time with an AI.

It's to give them a reason to spend less time looking at a screen.

## Demo

**Live demo:** https://offscreen-one.vercel.app/

> Judge instructions: create an account with any email address and a password of at least 8 characters. There is no email verification step, so you can be signed in within seconds.

**Demo video (63s, the real app end to end):**
[Watch on GitHub](https://github.com/Harsh-0986/OffScreen/blob/main/docs/media/demo.mp4) · [Download](https://raw.githubusercontent.com/Harsh-0986/OffScreen/main/docs/media/demo.mp4)

The complete experience is:

**Get a challenge → Put the phone down → Go outside → Take a photo → Come back → Let Gemma evaluate your discovery.**

## Code

GitHub repository: {% embed https://github.com/Harsh-0986/OffScreen %}

The project is an AI-powered web application with the AI workflow separated from the user interface, orchestrated as two explicit state graphs rather than a single opaque agent loop.

## How I Built It

The core of the project is **Gemma**, Google's open-weight model.

Gemma writes every challenge, looks at every photograph, and decides every score. Nothing in the app works without it.

The application uses **LangGraph** to orchestrate the workflow. There are two graphs, and both are deliberately boring:

```text
challenge:  START → load_context → generate_challenge → END

discovery:  START → load_challenge → analyze_photo → evaluate_discovery
                 → generate_feedback → save_discovery → update_profile → END
```

There is no autonomous loop and no self-reflection. Each node runs once. The whole system has exactly **one** conditional edge, and it is an error guard: if the challenge can't be found, the graph jumps straight to `END`, because there is no point paying for a vision call to judge a photograph against nothing.

Three decisions were made against the obvious implementation.

**1. One multimodal call, not four.** The textbook pipeline is identify → describe → evaluate → feedback. That's four model calls, and it lets the model contradict its own description. Instead, a single request returns the description *and* the evaluation together. The two-stage path is still in the codebase behind a flag so the two can be compared.

**2. Gemma ignores the function schema.** My first live call used the provider's structured-output helper. Gemma ignored the JSON schema I declared and returned its own key names — asked for `title`, it gave me `challenge_title`. So the schema is now written into the prompt as an annotated JSON skeleton, the reply is parsed and validated locally with Pydantic, and a validation failure buys the model exactly one chance to fix itself. Nothing the model returns is trusted.

**3. Personalization you can measure.** "Favour what the user likes" left to the model is a suggestion it may ignore, and you cannot check it afterwards. So the category is chosen *before* generation — about 60% weighted toward the user's favourites and 40% uniform exploration — and handed to the model as a constraint it cannot override. A test draws 2,000 seeds and asserts the ratio. A score isn't a vibe here; it's a number somebody checked.

The backend is FastAPI, Pydantic, and SQLite through SQLAlchemy; the frontend is Next.js. There are **176 tests, all hermetic** — no test makes a network call, none touches the real database, and the model is stubbed everywhere. The suite runs in about eighteen seconds and costs nothing, which meant I could run it after every single change.

## Why Does Open Innovation Matter?

The honest version of this answer starts with a limitation: **this MVP runs against Google's hosted AI Studio API, so photographs do leave the machine.** I'm not claiming local inference or privacy properties I haven't demonstrated.

What open AI actually bought me was three concrete things.

**1. It made the project possible in the time I had.** A multimodal model I could call with an API key, in an afternoon, for free at this scale, is what turned "an idea about putting the phone down" into something I could iterate on. The interesting work went into prompt design, evaluation, and agent structure rather than into access. For a project whose entire premise is an AI loop, that's the difference between shipping and not.

**2. Gemma's actual behaviour shaped the architecture.** Asked for a JSON schema through the provider's function calling, it returned its own field names. A closed API would have given me that same result — but with an open model I could inspect the failure, decide to stop trusting the tooling, and build the fix into my own prompt and validation layer. Every subsequent discovery followed the same pattern: see what the model does, then design around it. I now know it hedges with "this appears to be" when it's unsure, which is exactly the behaviour the prompts demand, and I know it doesn't reliably — both of which I learned by testing, not by reading a model card.

**3. The model is a configuration value, not an architecture.** The model id lives in an environment variable. That made one optimisation obvious: challenge writing is mostly text generation and barely uses vision, so splitting a small model for challenges and the larger one only for judging became a straightforward next step rather than a rewrite. It's only obvious because swapping models isn't a rewrite.

LangGraph matters for the same reason — the reason this agent is explainable is that its control flow is an open graph I can read. When the graph made a mistake, I found it because the whole path was six lines long and visible. That determinism is a property of choosing an open harness, not something I wrote.

## What Actually Happened When I Used It

This is the part I found most interesting, and most of it is wrong.

**The judge is genuinely strict.** I submitted a photograph of a walking shadow against a challenge asking for a dated plaque on a building. It came back `0/10`, `completed: false`, with: *"This is a great capture of city life and textures, but I couldn't spot a plaque or date in this frame!"* No score inflation, no encouragement to try again — it just told me the truth. That mattered more to me than a high score would have, because the obvious failure mode for an AI judge is being agreeable.

**It invented an object.** On the same photograph it correctly described the low angle, the mid-stride legs, and the warm afternoon light — and then titled the discovery *"Streetlight Silhouettes."* There is no streetlight in that frame. My prompts explicitly forbid inventing things that aren't visible, and it did anyway. This is a real hallucination that shipped, and it's the clearest example of why an AI evaluator needs a human who actually goes outside and checks.

**Its confidence is meaningless.** Both submissions returned `confidence: 1.0` — for the correct verdict and for the wrong one. A field that's always 1.0 carries no information at all. It's either a prompt problem or a calibration problem, and right now I can't tell which. The fix is a small labelled set of my own photographs with scores I'd defend, and measuring the model against them.

**Real usage found bugs that 169 tests missed.** The profile showed a streak of 0 and 0 completed challenges forever. Two separate bugs, in the same function: SQLite returns naive datetimes even from timezone-aware columns, so a timezone comparison always failed — meaning the streak would have worked perfectly on PostgreSQL, and the field I'd have migrated to later. And a counter was declared and returned by the API but never incremented anywhere in the codebase. Both only appeared once a real photograph went through the system. The tests had been asserting on in-memory objects; the new ones round-trip through the database, which is exactly the gap that let them through.

**The latency is real.** Generating a challenge takes about 40 seconds on the free tier. That's why the app pre-generates tomorrow's challenge while you're reading today's one — the wait happens once, quietly, instead of in front of you every morning.

## My Agent Session

I built Offscreen from the initial idea through implementation and submission planning with an agentic coding workflow — twenty-two commits, phase by phase, from a written specification.

You can see the development process here:

{% agent_session building-offscreen-an-outdoor-discovery-journal-from-spec-to-submission-nhxbo2 %}

## Prize Categories

I'm entering the **overall** prize, and **Best Use of Render** — the FastAPI backend and its Gemma calls run as a web service on Render.

I'm not entering the other partner categories. Nothing in this project uses Arduino, TabPFN, or Tinker, and a category is a claim that a technology did real work — not a list of things I could have used.

## Final Thought

There are already millions of apps competing for our attention.

I wanted to build one that does the opposite.

**Offscreen isn't trying to keep you here.**

It's trying to give you a reason to leave.

**One photo. One discovery. One reason to go outside.**
