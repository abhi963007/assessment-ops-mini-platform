# DECISIONS.md — Engineering Assumptions & Choices

## 1. Student Identity Resolution

**Decision:** Identify students by normalized email (primary) or normalized phone (fallback).

**Rationale:**
- The dataset contains the same student with wildly different email aliases (`anjali.kumar@gmail.com`, `a.njali.kumar+neet@gmail.com`, `an.j.ali..k.um.ar+neet@gmail.com`).
- Gmail ignores dots in the local part and everything after `+` is an alias.
- **Normalization:** lowercase → strip `+alias` → remove dots from local part (Gmail only).
- Phone normalization: strip all non-digit characters, take last 10 digits (removes country code variants like `+91`, `0091`, `91`).
- Name is **not** used for identity — only for display (normalized to title case, collapsed whitespace).

## 2. Deduplication Strategy

**Decision:** Two attempts are duplicates if ALL of:
1. Same student (by normalized identity)
2. Same test (by test name)
3. `started_at` within **7 minutes**
4. Answer similarity **≥ 92%**

**Canonical attempt:** The earliest `started_at` in a duplicate group becomes canonical. Later duplicates get `status=DEDUPED` and `duplicate_of_attempt_id` pointing to the canonical.

**Answer similarity formula:**
```
common_questions = intersection of question keys
matching = count where answers are identical
similarity = matching / len(common_questions)
```

**Why 92%?** This allows ~6 different answers out of 75 (JEE) or ~14 out of 180 (NEET), which accounts for minor edits between re-submissions while still catching true duplicates.

## 3. Scoring Without an Answer Key

**Decision:** Since the dataset does not include an answer key, all non-SKIP answers are counted as "correct" for scoring purposes.

**Rationale:**
- The assignment requires computing scores using `tests.negative_marking`.
- Without an answer key, we cannot determine correct vs. wrong.
- We treat all answered questions as correct and SKIP as skipped.
- The `compute_score` function accepts an optional `answer_key` parameter — when provided, it properly classifies correct/wrong.
- The `recompute` endpoint can be extended to accept an answer key in the future.

**Formula:**
```
score = correct × marking.correct + wrong × marking.wrong + skipped × marking.skip
accuracy = correct / (correct + wrong) × 100
net_correct = correct - wrong
```

## 4. Handling Messy Data

| Issue | Handling |
|-------|----------|
| **Gmail aliases** (`name+alias@gmail.com`) | Strip `+alias`, remove dots from local part |
| **Phone format chaos** (`+91 98765 43210`, `(0091)98765 43212`) | Strip non-digits, take last 10 |
| **Name variations** (`ANJALI KUMAR`, `anjali kumar`, `Anjali  Kumar`) | Normalize to title case, collapse whitespace |
| **Null email** (25 events) | Fall back to phone for identity |
| **Null phone** (11 events) | Use email for identity |
| **Null `submitted_at`** (partial submissions) | Store as-is, still score the answers present |
| **Duplicate `source_event_id`** | Allowed — same event can arrive from multiple channels; dedup logic handles it |
| **Malformed timestamps** | Parse with fallback; reject event if `started_at` is unparseable |

## 5. Database Design Choices

- **`normalized_email` / `normalized_phone` columns on `students`:** Indexed for fast identity lookups during ingestion. Raw values preserved in `email`/`phone`.
- **`raw_payload` on `attempts`:** Stores the original JSON event exactly as received, for auditability.
- **`explanation` JSONB on `attempt_scores`:** Stores the full scoring breakdown (marking scheme, counts, formula) for transparency.
- **`duplicate_of_attempt_id` self-FK:** Creates a chain from duplicate → canonical attempt.
- **Enum for `status`:** PostgreSQL native enum (`INGESTED`, `DEDUPED`, `SCORED`, `FLAGGED`) for type safety and query performance.

## 6. Structured Logging

**Decision:** Monolog-style JSON logs with per-request context.

Every log line includes:
- `timestamp` (ISO 8601 UTC)
- `level` (INFO, DEBUG, ERROR, etc.)
- `message`
- `channel` (http, db, dedup, scoring)
- `context` (request_id, attempt_id, student_id)
- `extra` (ip, user_agent, query_params, duration_ms)

**Implementation:**
- `request_id` (UUID) generated per HTTP request via middleware
- Stored in `contextvars.ContextVar` for thread-safe access across the call stack
- Request start/end logged with latency
- Dedup decisions logged with similarity scores
- Scoring runs logged with attempt_id, score, duration

## 7. Leaderboard Ranking

**Decision:** Best attempt per student (highest score), with tiebreakers:
1. Score (descending)
2. Accuracy (descending)
3. Net correct (descending)
4. Earliest submission (ascending)

Only `SCORED` and `FLAGGED` attempts are included (not `DEDUPED` or `INGESTED`).

## 8. Tech Stack Choices

| Choice | Reason |
|--------|--------|
| **FastAPI** | Async-ready, auto-generated OpenAPI docs, Pydantic validation |
| **SQLAlchemy 2.0** | Mature ORM, good PostgreSQL support, type hints |
| **Alembic** | Standard migration tool for SQLAlchemy |
| **React + Vite + TypeScript** | Fast dev experience, type safety |
| **Tailwind CSS** | Utility-first, rapid UI development |
| **Lucide React** | Lightweight icon library |
| **Axios** | Robust HTTP client with interceptors |
