Dataset Analysis & Architecture Guide
Dataset Summary (attempt_events.json)
Metric	Value
Total events	158
Unique students (after normalization)	~14
Tests	2 — JEE Mock 1 (75 Qs, 300 marks) and NEET Mock 1 (180 Qs, 720 marks)
Channels	web, email, whatsapp
Potential duplicate pairs	47 (same student + test + started_at within 7 min)
Edge Cases Found in the Data
1. Gmail Alias Mess (biggest challenge)
The same student appears with wildly different email variations:

anjali.kumar@gmail.com, a.njali.kumar+neet@gmail.com, an.j.ali..k.um.ar+neet@gmail.com, anjali..ku.mar+x@gmail.com
All normalize to → anjalikumar@gmail.com (strip dots + strip +alias)
2. Name Variations (case & whitespace)
"Anjali Kumar", "Anjali  Kumar" (double space), "ANJALI KUMAR", "anjali kumar"
"Rohan Nair" vs "ROHAN nair"
Decision needed: Identity is by email/phone, NOT name. Names get normalized for display only.
3. Phone Format Chaos
"+91 98765 43210", "00919876543210", "(+91) 98765-43212", "91-98765-43213", "(0091)98765 43212"
All normalize by stripping non-digits and taking last 10 digits.
4. Missing Data
25 events have null email → fall back to phone for identity
11 events have null phone → use email for identity
No event has both null (verified)
5. Partial Submissions
Some events have null for submitted_at → student started but never submitted. We store them and score what's there.
6. Duplicate source_event_ids
Some events share the same source_event_id (e.g., evt_fd7cb8fc66, evt_49a5cc9a7d, evt_b751bd385a) — these are re-sends from the coaching centre's system.
What We're Building — Architecture Overview
┌─────────────────┐     POST /api/ingest/attempts     ┌──────────────────────┐
│  attempt_events  │ ──────────────────────────────────▶│   FastAPI Backend    │
│     .json        │                                    │                      │
└─────────────────┘                                    │  1. Validate payload │
                                                       │  2. Normalize student│
                                                       │  3. Upsert student   │
       ┌───────────────────────────────────────────────│  4. Upsert test      │
       │                                               │  5. Store attempt    │
       ▼                                               │  6. Dedup check      │
┌─────────────┐                                        │  7. Score compute    │
│ PostgreSQL  │◀───────────────────────────────────────│  8. Structured logs  │
│             │                                        └──────────┬───────────┘
│ • students  │                                                   │
│ • tests     │         GET /api/attempts                         │
│ • attempts  │         GET /api/leaderboard          ┌───────────▼───────────┐
│ • scores    │         POST /flag, /recompute        │   React Frontend      │
│ • flags     │◀──────────────────────────────────────│                       │
└─────────────┘                                       │  • Attempts List      │
                                                      │  • Attempt Detail     │
                                                      │  • Leaderboard        │
                                                      └───────────────────────┘
Data Flow (step by step)
Ingestion Pipeline
Receive batch of events via POST /api/ingest/attempts
Validate — check required fields, repair what's fixable (timestamps)
Normalize student identity — Gmail alias normalization or phone digit extraction
Upsert student — find-or-create by normalized email/phone
Upsert test — find-or-create by test name
Store attempt — save with status=INGESTED, store full raw_payload
Dedup — for each new attempt, check existing attempts with same student + test + started_at within 7 min + answer similarity ≥ 92%. If duplicate → set status=DEDUPED and link duplicate_of_attempt_id
Score — for non-duplicate attempts, compute score using negative_marking config → status=SCORED
Dedup Logic (your key algorithm)
is_duplicate(attempt_a, attempt_b):
  same_student AND
  same_test AND
  |started_at_a - started_at_b| <= 7 minutes AND
  answer_similarity(a, b) >= 0.92
 
answer_similarity(a, b):
  common_questions = keys(a) ∩ keys(b)
  matching = count where a[q] == b[q]
  return matching / len(common_questions)
The earliest attempt becomes the canonical one; later duplicates point to it.

Scoring Formula
score = correct × 4 + wrong × (-1) + skipped × 0
accuracy = correct / (correct + wrong) × 100
net_correct = correct - wrong
Tech Stack & Project Structure
assessment/
├── docker-compose.yml
├── .env.example
├── README.md
├── DECISIONS.md
├── backend/
│   ├── requirements.txt
│   ├── alembic/              # DB migrations
│   ├── app/
│   │   ├── main.py           # FastAPI app + middleware
│   │   ├── models.py         # SQLAlchemy models (5 tables)
│   │   ├── schemas.py        # Pydantic request/response
│   │   ├── routes/
│   │   │   ├── ingest.py     # POST /api/ingest/attempts
│   │   │   ├── attempts.py   # GET /api/attempts, recompute, flag
│   │   │   └── leaderboard.py
│   │   ├── services/
│   │   │   ├── dedup.py      # Deduplication engine
│   │   │   ├── scoring.py    # Score computation
│   │   │   └── normalize.py  # Email/phone normalization
│   │   └── logging/
│   │       └── structured.py # Monolog-style JSON logger
│   └── alembic.ini
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── pages/
│   │   │   ├── AttemptsList.tsx
│   │   │   ├── AttemptDetail.tsx
│   │   │   └── Leaderboard.tsx
│   │   ├── components/
│   │   └── api/              # Axios/fetch wrappers
│   └── vite.config.ts
└── attempt_events.json
Key Decisions You'll Need to Defend
Decision	Rationale
Identity = normalized email first, phone fallback	Email is more reliable; phone formats are too varied
Gmail normalization: strip dots + strip +alias	Per Gmail spec, dots are ignored and + is alias
Canonical attempt = earliest started_at	First submission is the "real" one
Answer similarity threshold = 0.92	Allows ~6 different answers out of 75 (JEE) or ~14 out of 180 (NEET)
Null submitted_at = still ingest & score	Partial submissions are valid data; score what's available
Name normalization = lowercase + collapse whitespace	Only for display; not used for identity matching