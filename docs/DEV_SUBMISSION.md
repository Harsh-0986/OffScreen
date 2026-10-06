# Draft: DEV submission

> **Status: draft.** Everything in `[SQUARE BRACKETS]` needs a real photograph or a
> real measurement before this is submitted. Do not submit it as-is, and do not
> fabricate the testing results — the challenge explicitly asks you to show your
> work.

---

## Title

**Offscreen — I built an app whose success metric is you closing it**

## The problem

People consume enormous amounts of digital content but increasingly experience the
world through screens. Noticing something outside is a habit, and habits need
reasons. Every app on your phone is competing to give you one more reason to stay
inside it. I wanted to build the opposite.

## The idea

Give people a reason to leave the screen. One small, specific outdoor challenge a
day. You go and find it. You photograph it. An open-weight model looks at your
photograph and tells you what it sees. The journal remembers it. Then the app says
come back tomorrow — and until then, go outside.

## How it works

```
Challenge → go outside → photograph → Gemma → evaluation → journal
```

The product principle is stated in the code as a constraint: there is no feed, no
infinite scroll, no notifications, no likes, no streaks that punish absence. The
`/mission` screen has one sentence and one button, because the goal is that you
leave it.

## Why open AI?

[Gemma runs at the centre of the product, not as a feature bolted on. It writes
every challenge, judges every photograph, and decides the score. Nothing about the
app works without it.]

- **Accessibility of the model.** A hobbyist can get an API key and build a real
  multimodal product in an afternoon. That matters for a project whose entire
  premise is an AI loop — the interesting work was prompt design, evaluation
  calibration, and agent structure, not access.
- **Control over the model choice.** The model id is configuration, not code. I
  could compare a smaller faster model against a larger one by changing one
  environment variable, which is how I could evaluate the accuracy/speed tradeoff
  honestly.
- **An open-weight path exists.** Google publishes Gemma weights, so the design is
  not permanently welded to a hosted API. The service is isolated behind one
  interface, so pointing it at a local or self-hosted model is a change of
  implementation, not a rewrite. [I have not done this yet — see honest limits.]

### Honest limits

I want to be straight about this rather than overclaim. The MVP runs against
Google's hosted AI Studio API, so **photographs leave the machine**. I make no
claims about local inference or privacy that I have not tested. My reasons for
choosing Gemma are accessibility, configurability, and the fact that the open
weights mean I'm not locked in — not that I have demonstrated local running.

## What it is built with

| | |
| --- | --- |
| Model | Gemma 4 via the Gemini API |
| Orchestration | LangGraph — two linear state graphs |
| Backend | FastAPI, Pydantic, SQLAlchemy |
| Frontend | Next.js, Tailwind, TypeScript |

## Architecture in one diagram

Two LangGraph graphs, both linear, no autonomous loop:

```
challenge:  START → load_context → generate_challenge → END
discovery:  START → load_challenge → analyze_photo → evaluate_discovery
                   → generate_feedback → save_discovery → update_profile → END
```

The one branch is an error guard: a missing challenge short-circuits to `END` so
the model is never called against nothing.

## Three things that were harder than expected

**1. Gemma ignores the function schema.** Asked for a JSON shape with `title`, it
returned `challenge_title`. Provider-level structured output was unusable, so the
schema is now rendered into the prompt as an annotated JSON skeleton and validated
locally, with one self-repair attempt when validation fails. That repair loop fixed
a bad category value on its very first live run.

**2. One call, not four.** The obvious pipeline is identify → describe → evaluate →
feedback. That's four model calls and lets the model contradict itself. Sending one
multimodal request that returns description and evaluation together is faster and
more coherent — and the two-stage path is still there behind a flag to compare.

**3. Personalization you can measure.** "Favour what the user likes" left to the
model is a suggestion it may ignore. Picking the category deterministically —
weighted 60% toward favourites, 40% exploration — and passing it as a hard
constraint makes the split measurable. A test draws 2000 seeds and asserts the
ratio.

## Real-world test

[REQUIRED — this section is what the challenge is actually asking for. See the
checklist below. Do not submit without it.]

**What I did**

[Describe how many challenges you completed, where, and over what period.]

**Photos**

[Insert the real photographs. Three to five is plenty. Include at least one that
scored badly.]

**What worked**

- [ ]

**What didn't**

- [ ]

**What surprised me**

- [ ]

**Bugs I hit while actually using it**

[Genuinely useful to readers. Include the journal images failing, and the SQLite
lock taking the app down, if you hit them.]

## Screenshots

| | |
| --- | --- |
| Landing | [ ] |
| Today's challenge | [ ] |
| Mission mode | [ ] |
| Submission | [ ] |
| Result with score | [ ] |
| Journal | [ ] |

## What I would build next

- [ ] **Pre-generation is a workaround, not a solution.** Generating tomorrow's
      challenge in the background removes the wait, but the first run of the day is
      still slow. A smaller model for challenge writing and the larger one only for
      judging is the obvious split.
- [ ] **Weather and season.** A rainy-day challenge should not ask for sunlight.
      A few lines of context in the prompt.
- [ ] **Local inference.** The service interface is already isolated; running
      Gemma locally is an implementation swap, not a rewrite.
- [ ] **Better calibration.** A small labelled set of real photographs with human
      scores would let me measure whether the evaluator agrees with people.

## Repo

[URL] · MIT licensed
