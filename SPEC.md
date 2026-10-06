# Outside, Not Online

> One photo. One discovery. One reason to go outside.

## 1. Project Overview

Outside, Not Online is an AI-powered outdoor discovery journal.

The application gives users one small, interesting real-world challenge.
The user leaves the screen, explores their surroundings, takes a photograph,
and returns to the application.

Gemma analyzes the photograph, evaluates the discovery, generates a short
reflection, awards discovery points, and uses the user's history to
personalize future challenges.

The core product principle is:

    The app should encourage the user to leave the app.

This project is designed for the Hacktoberfest 2026 Open-Source AI Challenge:
"Touch Grass".

---

# 2. Goals

## Primary Goals

1. Generate interesting outdoor discovery challenges.
2. Get users physically outside.
3. Allow users to submit a photograph.
4. Use Gemma to understand the photograph.
5. Evaluate whether the photograph satisfies the challenge.
6. Maintain a personal outdoor discovery journal.
7. Personalize future challenges based on previous discoveries.
8. Keep the application simple enough to build and polish within the
   hackathon timeframe.

## Secondary Goals

1. Demonstrate meaningful use of an open-weight Gemma model.
2. Demonstrate an agent/workflow architecture with LangGraph.
3. Produce a strong visual demo.
4. Produce a compelling DEV Community write-up.

---

# 3. Non-Goals

The MVP will NOT attempt to:

- monitor phone screen time
- detect Instagram/TikTok usage
- build an Android application
- build an iOS application
- track GPS continuously
- build a social network
- implement followers
- implement likes/comments
- build a recommendation feed
- build complex gamification
- train/fine-tune Gemma
- build a custom computer vision model
- require hardware

These features may be considered after the MVP.

---

# 4. Core User Experience

The entire product should revolve around this loop:

    OPEN APP
        ↓
    Receive today's challenge
        ↓
    Leave the application
        ↓
    Explore outside
        ↓
    Take a photograph
        ↓
    Return
        ↓
    Upload photograph
        ↓
    Gemma analyzes photograph
        ↓
    Discovery evaluation
        ↓
    Points + journal entry
        ↓
    Next challenge

The application should never encourage endless usage.

---

# 5. Example Experience

## User opens the application

Display:

    TODAY'S DISCOVERY

    Find something that looks like a face.

    Don't overthink it.

    Go outside and find it.

    [ START ADVENTURE ]

After pressing START:

    Your mission has started.

    Close the app.

    Go find something interesting.

The user leaves.

---

## User returns

They upload a photograph.

Gemma receives:

    Challenge:
    "Find something that looks like a face."

    Image:
    <uploaded image>

Gemma returns:

    {
      "challenge_completed": true,
      "discovery": "A tree whose branches resemble a face",
      "confidence": 0.91,
      "description": "...",
      "interesting_fact": "...",
      "score": 10,
      "feedback": "You found it. The branches really do resemble a face."
    }

The UI displays:

    DISCOVERY FOUND

    🌳 Branches that look like a face

    +10 Discovery Points

    "The branches create a surprisingly convincing
     facial outline."

    [ VIEW JOURNAL ]

---

# 6. Technology Stack

## Frontend

- Next.js
- TypeScript
- Tailwind CSS
- Framer Motion
- shadcn/ui where useful

## Backend

- Python
- FastAPI
- Pydantic

## AI

- Gemma 4
- Google AI Studio / Gemini API

Preferred model configuration:

    gemma-4-26b-a4b-it

Keep the model configurable through environment variables.

    GEMMA_MODEL=gemma-4-26b-a4b-it

If a different Gemma 4 model is required because of API availability,
change only the configuration.

## Agent Framework

- LangChain
- LangGraph

Use LangGraph for orchestration/state.

Do NOT build unnecessary chains simply to demonstrate LangChain.

## Database

MVP:

- SQLite
- SQLAlchemy

Future:

- PostgreSQL

## Image Storage

MVP:

- local filesystem

Future:

- object storage

---

# 7. High-Level Architecture

                    ┌───────────────────┐
                    │     Next.js       │
                    │     Frontend      │
                    └─────────┬─────────┘
                              │
                              │ HTTP
                              ▼
                    ┌───────────────────┐
                    │      FastAPI      │
                    │       API         │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │    LangGraph      │
                    │   Agent Workflow  │
                    └─────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             ┌─────────────┐     ┌─────────────┐
             │   Gemma 4   │     │   SQLite    │
             │ AI Studio   │     │  Database   │
             └─────────────┘     └─────────────┘

---

# 8. LangGraph Architecture

The application should use a small state graph.

    START
      ↓
    LoadContext
      ↓
    GenerateChallenge
      ↓
    END

For photo submission:

    START
      ↓
    LoadChallenge
      ↓
    AnalyzePhoto
      ↓
    EvaluateDiscovery
      ↓
    GenerateFeedback
      ↓
    SaveDiscovery
      ↓
    UpdateProfile
      ↓
    END

Do not create an autonomous loop.

The graph should be deterministic and easy to explain.

---

# 9. Agent State

Create:

    backend/app/graph/state.py

Example:

    class DiscoveryState(TypedDict, total=False):

        user_id: str

        current_challenge: dict

        challenge_history: list

        image_path: str

        image_mime_type: str

        image_analysis: dict

        evaluation: dict

        feedback: dict

        user_profile: dict

        discovery: dict

        error: str

The state should be serializable.

---

# 10. Challenge Generation

## Input

The challenge generator receives:

    user profile
    previous challenges
    previous discoveries
    current date
    optional weather/context

MVP does not require weather.

Example:

    {
      "user_profile": {
        "favorite_categories": [
          "nature",
          "architecture"
        ]
      },
      "recent_challenges": [
        "Find something symmetrical"
      ],
      "recent_discoveries": [
        "old tree",
        "red door"
      ]
    }

## Output

The model MUST return structured JSON.

Example:

    {
      "title": "Unexpected Symmetry",
      "prompt": "Find something outside that is surprisingly symmetrical.",
      "difficulty": 2,
      "estimated_minutes": 20,
      "category": "observation"
    }

---

# 11. Challenge Categories

Initial categories:

    observation
    nature
    architecture
    color
    texture
    animals
    people
    light
    shapes
    history
    creativity

Examples:

    Find something that looks like a face.

    Find something older than you.

    Find the strangest texture you can see.

    Find two things that are exactly the same color.

    Find something you normally walk past.

    Find evidence that an animal was here.

    Find something perfectly symmetrical.

    Find something that would make a good album cover.

---

# 12. Photo Analysis

The photo analysis node sends:

    challenge
    image
    analysis instructions

to Gemma.

The Gemini API supports image input alongside text, so the image can be passed
as multimodal model input. :chatgpt-content-reference{index="2"}

Prompt structure:

    SYSTEM:

    You are the visual discovery evaluator for
    "Outside, Not Online".

    Your job is to evaluate whether the user's photograph
    reasonably satisfies the given outdoor discovery challenge.

    Be encouraging.

    Do not invent objects that are not visible.

    Return JSON only.

    USER:

    Challenge:
    {challenge}

    Analyze this photograph.

---

# 13. Photo Evaluation Schema

Gemma should return:

    {
      "completed": true,
      "confidence": 0.0,
      "what_was_found": "...",
      "visual_description": "...",
      "reasoning_summary": "...",
      "interesting_detail": "...",
      "score": 0,
      "feedback": "..."
    }

Score range:

    0 - 10

Suggested scoring:

    0-2   Challenge not satisfied
    3-5   Weak match
    6-7   Reasonable match
    8-9   Strong discovery
    10    Excellent / creative discovery

The backend MUST validate the response with Pydantic.

Never trust raw model JSON.

---

# 14. Important AI Rule

The model must NOT determine facts that cannot reasonably be inferred
from the photograph.

For example:

BAD:

    "This tree is exactly 80 years old."

GOOD:

    "This appears to be a mature tree."

If identification is uncertain:

    "This appears to be..."

rather than:

    "This is definitely..."

---

# 15. Discovery Journal

Every completed challenge creates a journal entry.

Example:

    {
      "id": "...",
      "user_id": "...",
      "challenge_id": "...",
      "image_url": "...",
      "title": "A Face in the Trees",
      "description": "...",
      "category": "nature",
      "score": 9,
      "created_at": "..."
    }

The journal should display discoveries visually.

---

# 16. User Profile

Keep the profile intentionally small.

    UserProfile

        id
        display_name

        total_points

        discoveries_count

        current_streak

        favorite_categories

        completed_challenges

        outdoor_minutes_estimate

        created_at

        updated_at

The profile should NOT become a complicated social system.

---

# 17. Personalization

After each discovery, update:

    favorite_categories

For example:

    nature: 7
    architecture: 2
    colors: 4
    textures: 1

Future challenges should slightly favor categories the user enjoys,
while still introducing variety.

Example:

    60% familiar preferences
    40% exploration

Do not use an ML recommendation system.

Simple deterministic personalization is enough for MVP.

---

# 18. Database Schema

Tables:

    users

    challenges

    discoveries

    user_preferences

Suggested relationships:

    User
      │
      ├── Challenges
      │
      └── Discoveries

Challenge:

    id
    user_id
    title
    prompt
    category
    difficulty
    estimated_minutes
    status
    created_at
    completed_at

Discovery:

    id
    challenge_id
    user_id
    image_path
    title
    description
    score
    confidence
    category
    ai_feedback
    created_at

---

# 19. API Design

## GET /health

Response:

    {
      "status": "ok"
    }

---

## POST /api/challenges/generate

Generate today's challenge.

Response:

    {
      "challenge": {
        "id": "...",
        "title": "...",
        "prompt": "...",
        "category": "...",
        "difficulty": 2,
        "estimated_minutes": 20
      }
    }

---

## GET /api/challenges/today

Return current challenge.

---

## POST /api/discoveries

Multipart request:

    image
    challenge_id

Backend:

    validate image
    save image
    invoke LangGraph
    analyze image
    evaluate challenge
    save discovery

Response:

    {
      "discovery": {
        "completed": true,
        "score": 9,
        "title": "...",
        "feedback": "..."
      }
    }

---

## GET /api/journal

Return user discoveries.

---

## GET /api/profile

Return:

    points
    discoveries
    streak
    favorite categories

---

# 20. Frontend Pages

## /

Landing page.

Show:

    OUTSIDE,
    NOT ONLINE.

    One photo.
    One discovery.
    One reason to go outside.

CTA:

    [ START EXPLORING ]

---

## /today

Today's challenge.

Large typography.

Minimal UI.

Example:

    TODAY'S DISCOVERY

    Find something that
    looks like a face.

    ~20 minutes

    [ START ]

After starting:

    Mission started.

    Close this app.

    Go outside.

---

## /submit

Photo submission.

Options:

    [ Take Photo ]

    [ Upload Photo ]

After selecting:

    [ Submit Discovery ]

---

## /result

Show:

    discovery image

    challenge

    AI interpretation

    score

    feedback

    points earned

CTA:

    [ ADD TO JOURNAL ]

---

## /journal

Grid-based visual journal.

Each discovery:

    image
    title
    date
    score

---

## /profile

Show:

    Total discoveries
    Discovery points
    Current streak
    Favorite categories

Keep this page simple.

---

# 21. UI Design Principles

The UI should feel like an anti-social-media application.

Avoid:

    infinite scrolling
    notifications
    feeds
    excessive cards
    engagement loops

Prefer:

    large typography
    photography
    whitespace
    short copy
    minimal navigation

The app should visually communicate:

    "Go outside."

---

# 22. AI Prompt Architecture

Create separate prompt files.

    backend/app/prompts/

        challenge_generation.py
        photo_analysis.py
        discovery_evaluation.py
        feedback.py
        personalization.py

Do not put large prompts directly inside API routes.

---

# 23. Gemma Service

Create:

    backend/app/services/gemma.py

Responsibilities:

    initialize Gemini client
    call Gemma
    handle image input
    enforce structured output
    handle retries
    normalize model responses

Environment:

    GEMINI_API_KEY=
    GEMMA_MODEL=gemma-4-26b-a4b-it

The API key MUST never be exposed to the frontend.

Google's current setup uses an API key generated through AI Studio and exposed
to the application through an environment variable. :chatgpt-content-reference{index="3"}

---

# 24. LangGraph Service

Create:

    backend/app/graph/

        __init__.py
        state.py
        nodes.py
        graph.py

Nodes:

    load_context
    generate_challenge
    load_challenge
    analyze_photo
    evaluate_discovery
    generate_feedback
    save_discovery
    update_profile

Graph creation:

    build_challenge_graph()

    build_discovery_graph()

Keep challenge generation and discovery evaluation as separate graphs.

---

# 25. LangChain Usage

Use LangChain for:

    structured model calls
    prompt management
    model integration
    LangGraph orchestration

Do NOT use LangChain for:

    basic HTTP requests
    database CRUD
    file uploads
    authentication

The current LangChain ecosystem separates core functionality and integrations,
so keep the Google/Gemini integration isolated from application logic. :chatgpt-content-reference{index="4"}

---

# 26. Error Handling

Gemma can fail.

The application must handle:

    invalid JSON
    API timeout
    rate limit
    image too large
    unsupported MIME type
    model unavailable
    safety block
    empty response

Fallback:

    "We couldn't evaluate your discovery right now.
     Your photo is saved. Try again."

Never expose stack traces to the user.

---

# 27. Image Handling

Allowed MVP types:

    image/jpeg
    image/png
    image/webp

Recommended maximum:

    10 MB

Resize very large images before sending them to the model.

The Gemini API supports common image MIME types including JPEG, PNG and WebP. :chatgpt-content-reference{index="5"}

For the MVP, inline/base64 image input is sufficient for small photos.
Google also provides a File API for larger or repeatedly reused files. :chatgpt-content-reference{index="6"}

---

# 28. Phase 0 — Repository Setup

Goal:

Create a clean monorepo.

Structure:

    outside-not-online/

        frontend/
        backend/

        README.md
        spec.md
        .gitignore
        .env.example

Backend:

    backend/
        app/
            main.py

            api/
            graph/
            models/
            schemas/
            services/
            prompts/
            db/

        tests/

        requirements.txt

Frontend:

    frontend/
        app/
        components/
        lib/
        public/

Acceptance criteria:

    frontend runs
    backend runs
    /health returns OK

---

# 29. Phase 1 — Gemma Connection

Goal:

Make one successful AI Studio → Gemma request.

Tasks:

- create AI Studio API key
- configure GEMINI_API_KEY
- configure GEMMA_MODEL
- implement Gemma service
- test text generation
- test structured JSON response

Acceptance:

    POST /api/test/gemma

returns:

    {
      "success": true
    }

Do not continue until this works.

---

# 30. Phase 2 — Challenge Generator

Implement:

    GenerateChallenge

Input:

    user profile
    previous challenges

Output:

    validated Challenge schema

Acceptance:

    User can request a challenge.

Example:

    Find something outside
    that looks like a face.

---

# 31. Phase 3 — Photo Analysis

Implement:

    image upload
    image validation
    Gemma multimodal request

Acceptance:

User can upload:

    photo

and receive:

    visual description

Do not implement scoring yet.

---

# 32. Phase 4 — Challenge Evaluation

Connect:

    challenge
          +
        photo
          ↓
        Gemma
          ↓
      evaluation

Acceptance:

    completed
    confidence
    score
    feedback

are returned as validated structured data.

---

# 33. Phase 5 — Database

Implement:

    users
    challenges
    discoveries
    preferences

Acceptance:

A completed discovery persists after restarting the backend.

---

# 34. Phase 6 — Journal

Build:

    /journal

Display:

    photo
    title
    score
    date

Acceptance:

After completing a challenge, the result appears automatically in the journal.

---

# 35. Phase 7 — Personalization

Implement basic preference tracking.

Example:

    User completed:

    5 nature challenges
    2 architecture challenges
    1 color challenge

Future generation prompt:

    User enjoys nature discoveries.

    Generate a new challenge with a nature-related concept,
    but do not repeat previous challenges.

Acceptance:

Two consecutive challenges should not be identical.

---

# 36. Phase 8 — Frontend Polish

Build the complete experience:

    Landing
       ↓
    Today's Challenge
       ↓
    Mission Mode
       ↓
    Upload
       ↓
    AI Evaluation
       ↓
    Result
       ↓
    Journal

Animations:

    page transitions
    challenge reveal
    score animation
    journal entry appearance

Do not add animations that slow down the experience.

---

# 37. Phase 9 — Real Outdoor Test

This is mandatory.

Actually take the application outside.

Complete at least:

    3 different challenges

Capture:

    screenshots
    photographs
    failures
    unexpected AI responses

Record what worked and what didn't.

This material should become part of the DEV submission.

The challenge specifically encourages participants to actually take their project
outside and use it. :chatgpt-content-reference{index="7"}

---

# 38. Phase 10 — Hackathon Polish

Add:

## Empty states

    No discoveries yet.

    Go outside and find something.

## Loading states

    Looking closely...

    Finding something interesting...

## Error states

    The AI couldn't judge this one.

## Demo data

Prepare 5-8 completed discoveries.

Do NOT fake the final demo.

Use real photos taken during testing.

---

# 39. Optional Features

Only implement these after MVP is stable.

## Weather-aware challenges

Example:

    Rainy day

    Find something that reflects light.

## Location-aware challenges

Example:

    You are near a park.

    Find something living.

Do not implement continuous location tracking.

## Voice

User can say:

    "Give me something interesting."

AI responds with a challenge.

## Shareable weekly journal

Generate:

    "My Week Outside"

with the user's discoveries.

---

# 40. Optional Arduino UNO Q Extension

Do NOT make Arduino part of the MVP.

If the core application is complete, build:

    UNO Q
       ↓
    physical button
       ↓
    trigger challenge
       ↓
    LED/display
       ↓
    "GO OUTSIDE"

This can target the Best Use of Arduino category.

The Hacktoberfest challenge explicitly includes an Arduino category for projects
using the UNO Q for AI, sensing/acting, or model optimization. :chatgpt-content-reference{index="8"}

---

# 41. Testing Strategy

## Backend

Test:

    challenge generation
    image validation
    AI response parsing
    score validation
    database persistence

## AI

Create fixed test cases:

    obvious success
    obvious failure
    ambiguous image
    unrelated image
    poor-quality image

Example:

    Challenge:
    "Find something red."

    Image:
    red flower

Expected:

    completed = true

---

# 42. Security

Never expose:

    GEMINI_API_KEY

to the browser.

Validate:

    file type
    file size
    request body

Never execute model-generated code.

Sanitize filenames.

Use generated UUIDs for uploaded images.

---

# 43. Performance

Target:

    Challenge generation < 10 seconds

    Photo analysis < 15 seconds

    Normal API response < 500ms

These are targets, not hard requirements.

Avoid multiple unnecessary model calls.

For photo submission, prefer:

    one multimodal Gemma call

rather than:

    identify image
        ↓
    describe image
        ↓
    evaluate image
        ↓
    generate feedback

unless testing shows that one call is insufficient.

---

# 44. MVP Definition

The MVP is COMPLETE when a user can:

1. Open the application.
2. Receive an AI-generated outdoor challenge.
3. Start the challenge.
4. Leave the application.
5. Take a photograph outside.
6. Return to the application.
7. Upload the photograph.
8. Have Gemma analyze it.
9. Receive a completion score.
10. Receive AI feedback.
11. Save the discovery.
12. See it in their journal.
13. Receive a different future challenge.

Everything else is optional.

---

# 45. Demo Script

The final demo should take approximately 2 minutes.

## Scene 1

Open app.

Show:

    TODAY'S DISCOVERY

    Find something that looks like a face.

Click:

    START ADVENTURE

Show:

    Close this app.

    Go outside.

---

## Scene 2

Cut to outdoor footage.

Show yourself finding something.

Take photograph.

---

## Scene 3

Return to application.

Upload photograph.

Show:

    Gemma analyzing...

---

## Scene 4

Result:

    DISCOVERY FOUND

    A face hidden in the branches.

    Score: 9/10

    +9 Discovery Points

---

## Scene 5

Open journal.

Show:

    YOUR WEEK OUTSIDE

    5 discoveries
    83 points
    4 outdoor sessions

---

## Final screen

    Outside, Not Online

    The goal was never to keep
    you in the app.

    It was to get you outside.

---

# 46. Hackathon Positioning

Primary category:

    Hacktoberfest Open-Source AI Challenge
    "Touch Grass"

Potential partner category:

    Best Use of Gemma

Optional:

    Best Use of Arduino
    Best Use of Sentry
    Best Use of ElevenLabs

Do not add partner technologies solely for prize eligibility.

Each technology should have a meaningful role.

The challenge has a $250 overall prize and a $200 Best Use of Gemma category,
with submissions due October 11, 2026. :chatgpt-content-reference{index="9"} :chatgpt-content-reference{index="10"}

---

# 47. DEV Submission

The post should explain:

## Problem

People consume enormous amounts of digital content but increasingly
experience the world through screens.

## Idea

Give people a reason to leave the screen.

## How it works

    Challenge
       ↓
    Outdoor discovery
       ↓
    Photograph
       ↓
    Gemma
       ↓
    Evaluation
       ↓
    Journal

## Why open AI?

Explain:

- model accessibility
- ability to build around an open-weight model
- model choice/control
- AI running as the core of the product

Do not make unsupported claims about privacy or local inference if the MVP
uses the Google AI Studio API.

## Real-world test

Include:

- actual outdoor photos
- failures
- successful missions
- screenshots
- what you learned

The submission requirements specifically ask participants to show their work
and explain why open innovation matters for their project. :chatgpt-content-reference{index="11"}

---

# 48. Final Definition of the Product

Outside, Not Online is NOT:

    another AI chatbot
    another social network
    another productivity dashboard
    another photo-sharing app

It is:

    An AI-powered outdoor discovery loop.

The AI creates the reason.

The real world provides the experience.

The photograph provides the evidence.

Gemma turns the experience into a story.

The journal remembers it.

And then the app tells you:

    "Come back tomorrow."
    "Until then, go outside."

---

# 49. Build Priority

Priority 1:

    Gemma connection
    Challenge generation
    Photo upload
    Photo analysis
    Evaluation
    Database
    Journal

Priority 2:

    Beautiful UI
    Personalization
    Animations
    Real-world testing

Priority 3:

    Weather
    Voice
    Location
    Arduino
    Weekly recap

If time runs out:

    STOP AFTER PRIORITY 1.

A polished small project is better than a large unfinished one.
