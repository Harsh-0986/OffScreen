# Hyperframes Composition Brief: Offscreen

## Objective

Create a short launch-style brag video for **Offscreen**, an AI-powered outdoor
discovery journal whose premise is that it wants you to close it.

## Output

- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: **21 seconds** (4 scenes: 4.5 + 4.5 + 4.0 + 8.0)

## Source Material

- Project root: `/Users/harshrohitshah/WebstormProjects/hackathons/hacktoberfest-2026-week1`
- Primary files read: `frontend/src/app/page.tsx`, `frontend/src/app/globals.css`,
  `frontend/src/app/layout.tsx`, `frontend/src/app/mission/page.tsx`,
  `frontend/src/app/today/page.tsx`, `frontend/src/app/result/page.tsx`,
  `frontend/src/app/journal/page.tsx`, `README.md`
- Product name: Offscreen
- Tagline: *a photo walk, one challenge at a time*
- Strongest claim: **"The goal was never to keep you in the app."**
- Key UI moment to recreate: **mission mode** — giant display type, one button,
  huge negative space. Also: today's challenge card, and the result card with the
  score count-up.

### Copy that must appear verbatim

- `OFFSCREEN`
- `The goal was never to keep you in the app.`
- `TODAY'S DISCOVERY`
- `Find something that looks like a face.`
- `~20 MIN` · `DIFFICULTY 2 / 4` · `LOOKING FOR: NATURE`
- `MISSION STARTED`
- `Close this app.`
- `Go outside.`
- `I'M BACK`
- `9` / `/10`
- `You found it. The branches really do resemble a face.`
- `+9 DISCOVERY POINTS`
- `Come back tomorrow. Until then, go outside.`

All of this copy exists in the project's real UI or its own README. Do not
invent product claims. The score of 9/10 and the feedback line are the app's own
sample output shape, not invented statistics.

## Creative Direction

- Tone preset: **deadpan**
- Creative direction: an anti-social network that wants you to leave, presented
  with complete sincerity
- Interpretation: long holds, huge empty space, almost no motion. The comedy comes
  from stillness. Every fast, flashy convention is what the product is rejecting,
  so the video rejects it too. No bouncing, no gradients as decoration, no
  whooshes, no beat hits on the punchline.
- Angle: the app's manifesto *is* the joke. The most compelling product moment is
  the screen whose entire purpose is to end the session.
- Hook: paper, then **OFFSCREEN**, then one line held long enough to read:
  *"The goal was never to keep you in the app."* No motion in the first beat.
- Outro: journal strip settles, then `Come back tomorrow. Until then, go outside.`
  No call to action.
- Avoid: generic SaaS language, abstract filler visuals, unrelated redesign,
  bouncy easing, neon, purple gradients, dark-mode futurism.

## Visual Identity

- Background: `#faf8f4` (paper)
- Text: `#16150f` (ink) · soft `#57544a` · faint `#8b877b`
- Accent: `#486b3f` (moss) — **score only**, nothing else
- Lines: `#e4dfd4`
- Display font: **Inter Tight 800**, local `assets/fonts/intertight-*.ttf`
- Body font: **Fraunces italic 400**, local `assets/fonts/fraunces-*.ttf`
- Both are self-hosted with `@font-face` — **no runtime network fetch**
- Visual references: the mission screen (empty space is the design), the
  letterspaced eyebrow style, the photograph-as-physical-print shadow

### Placeholder note

No real photograph is available to this composition, and none may be fabricated
as if it were a real discovery. The result scene's photo frame is a **tinted
stand-in** (soft moss→ink gradient in a printed-photo frame) captioned
`the photograph you brought back`. Replace it with a real outdoor photograph if
one is available.

## Storyboard

Contract lives in `brag-output/brag-plan.md`.

1. **Hook** — 4.5s — wordmark, then the manifesto line typed on and held.
2. **Today's discovery** — 4.5s — challenge card; three meta items arrive one at a
   time, then hold as a set.
3. **Mission mode** — 4.0s — the centerpiece. Giant two-line statement, timer
   counting 00:00→00:04, one cursor press on `I'M BACK`.
4. **Result → journal → final line** — 8.0s — photo frame, score counts up to 9,
   feedback line, points line, card settles into a journal strip, final line held.

## Audio

- Audio role: warm bed, sparse. Confident enough to be quiet.
- Audio arc: near-silence into a low bed at scene 1; three soft interface ticks
  across scene 2; one muted press in scene 3; ticks through the scene 4 count-up;
  fade out under the final line. No risers, no impacts.
- Music: `assets/music/happy-beats-business-moves-vol-1-by-ende-dot-app.mp3`
- Music treatment: `data-volume="0.16"`, start at 0, duration 21, fade handled by
  the bed ending low under the closing line. No swell on the punchline.
- Music cue guidance: bundled preset, ~120.19 BPM, window 0–25s.
  - `// beat-locked: 17.02s` — score count-up completes (strong cue 17.02)
  - `// beat-locked: 18.02s` — journal strip settles (strong cue 18.02)
  - `// beat-grid: meta 1 at 6.52s, meta 2 at 7.02s, meta 3 at 7.52s`
    (three consecutive beats; each is a short label, and all three hold together
    afterwards, so reading stays comfortable)
- Audio-reactive treatment: **none**. This tone must not pulse. Documented as a
  deliberate choice, not an extraction failure.
- Audio-coupled moments:
  - Scene 2 — three meta labels assemble, one soft tick each, on the beat grid
  - Scene 3 — one muted button press at the cursor contact
  - Scene 4 — ticks stepping through the score count-up, landing on the cue
- SFX selection guidance: low, dry, non-metallic interface sounds. Avoid anything
  with a bright transient — this is a paper-coloured room. Chosen files are in
  `assets/sfx/`.
- Exact SFX choice: made by Hyperframes from `assets/sfx/`; timestamps must match
  the implemented motion exactly.
- Audio files: music copied to `composition/assets/music/`; SFX in `composition/assets/sfx/`.

## Hyperframes Instructions

- Show the real UI: recreate mission mode, the challenge card, and the result card
  faithfully in HTML/CSS using the project's tokens and fonts.
- All text readable: short labels ≥0.8s settled; the manifesto line ≥2.5s; the
  final line ≥2.0s. If copy does not fit the scene, cut it — do not speed it up.
- Duration must stay within 15–25s.
- Include the planned audio layer.
- Keep creation and rendering local.

### Implementation constraints (from hyperframes-core)

- Standalone root `index.html`, **no `<template>`** wrapper around the root.
- Root sized explicitly `1920x1080`; scene containers `width:100%; height:100%`.
- Full-bleed background on a **child** element (`position:absolute; inset:0`), never
  on the root itself.
- One `gsap.timeline({ paused: true })`, registered synchronously at
  `window.__timelines["main"]`, key matching root `data-composition-id="main"`.
- All `<audio>` elements are **direct children of the root**.
- Do not `gsap.set()` later-scene clips; the framework owns clip visibility.
- No `Date.now()`, no `Math.random()`, no `repeat: -1`, no network fetch at render
  time (fonts and audio are local).
- No `<br>` in body text. The mission statement's two lines are separate elements.
- The timer and score count-up must be **pre-built stacked elements toggled by
  timeline sets**, not timers or callbacks — every frame must be reproducible from
  its time value alone.
