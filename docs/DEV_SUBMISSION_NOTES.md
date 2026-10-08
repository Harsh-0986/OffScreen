# Publishing notes — not part of the post

Everything in `DEV_SUBMISSION.md` is the post body, ready to paste. This file is
for you.

## Before you publish

- [ ] **Create the DEV article as a draft first**, paste the body in, then read
      it in DEV's own editor. That's the version judges see.
- [ ] **Set `ai_disclosure_level`** when creating the article. This post was
      drafted with agent assistance, so `some_ai` is the honest value. It is an
      article setting, not something in the body.
- [ ] **Publish the agent session** or the `{% agent_session %}` tag will 404 for
      judges. Open the session while signed in and use **Make Public**:
      https://dev.to/agent_sessions/building-offscreen-an-outdoor-discovery-journal-from-spec-to-submission-nhxbo2
- [ ] **Tags**: `devchallenge`, `hf26challenge` — both required. Add `python`,
      `nextdotjs`, `langgraph`, `gemma` if you want reach.
- [ ] **Demo video**: DEV won't reliably render a `<video>` tag, so the post links
      to the file in the repo. If you want it inline, upload to YouTube (or
      unlisted YouTube) and swap in `{% embed <youtube-id> %}`.

## Judging criteria, for reference

1. **Writing Quality** — weighted most heavily
2. Relevance to the Prompt and Theme
3. Creativity
4. Technical Execution
5. Use of Partner Technology (optional)

That's why the "What Actually Happened" section is the longest part of the post.
It's the section that separates a build story from a product description.

## What changed from your draft, and why

**Fixed**

- **Prize categories.** "Best Use of Gemma" and "Best Use of LangGraph" aren't
  categories on this challenge page. The real ones are Overall, Render, TabPFN,
  Tinker, Arduino. Replaced with Overall + Best Use of Render, which is honest —
  the backend genuinely runs there.
- **Product name.** The draft said "Outside, Not Online" throughout while the
  product, repo, and landing page say Offscreen. Now Offscreen, with the
  manifesto implied rather than repeated.
- **Challenge examples.** Replaced the invented ones with real generated output
  from your own runs — "Shadow Play" and "The Ghost Sign". Real ones are more
  credible than plausible ones.
- **Flow diagram.** It showed analysis and evaluation as separate steps. You
  deliberately built one multimodal call, which is one of the better stories in
  the project. Now says so.
- **`My Agent Session` was missing its `##`** heading.
- **Added testing credentials.** The Official Rules ask for them when an app
  requires login.
- **Added the video links.** There was only a bare live link before.

**Strengthened**

- **"Why open" was philosophical.** The brief asks where the open approach worked
  *better* than a closed one. Replaced with three concrete answers, each grounded
  in something that actually happened — including Gemma's schema failure, which
  is the best evidence that an open model let me design around its behaviour.
- **Added the honest limitation up front** — hosted API, so photos leave the
  machine. The brief warns against unsupported privacy claims, and conceding it
  makes everything after it more credible.
- **Added the real-world test section** from your demo run: the 0/10 miss, the
  hallucinated streetlight, the meaningless 1.0 confidence, and the two profile
  bugs.
- **Undersold technical work** is now visible: 176 hermetic tests, the two linear
  graphs with one branch, and personalization measured over 2,000 seeds.

**Kept exactly as written**

The Final Thought, and the short declarative sentences in "What I Built". They're
the strongest writing in the draft and I didn't touch them.
