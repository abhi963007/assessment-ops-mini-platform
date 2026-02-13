<div align="center">

# Assessment Ops Mini Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**A full-stack platform that ingests messy student assessment data, deduplicates noisy events, computes scores with negative marking, and serves a beautiful analytics dashboard.**

[Getting Started](#-getting-started) · [Features](#-features) · [API Reference](#-api-reference) · [Architecture](#-architecture) · [Decisions](#-design-decisions)

</div>

---

## Screenshots

<div align="center">
<table>
<tr>
<td align="center"><b>Attempts List</b></td>
<td align="center"><b>Leaderboard</b></td>
</tr>
<tr>
<td><img src="docs/screenshots/attempts_list.png" alt="Attempts List" width="450"/></td>
<td><img src="docs/screenshots/leaderboard.png" alt="Leaderboard" width="450"/></td>
</tr>
<tr>
<td align="center"><b>Attempt Detail</b></td>
<td align="center"><b>API Docs (Swagger)</b></td>
</tr>
<tr>
<td><img src="docs/screenshots/attempt_detail.png" alt="Attempt Detail" width="450"/></td>
<td><img src="docs/screenshots/api_docs.png" alt="API Docs" width="450"/></td>
</tr>
</table>
</div>

---

## Features

| Feature | Description |
|---------|-------------|
| **Batch Ingestion** | POST hundreds of messy attempt events in one call |
| **Smart Deduplication** | Detects duplicates via 7-min time window + 92% answer similarity |
| **Identity Resolution** | Normalizes Gmail aliases (`a.b+tag@gmail.com` → `ab@gmail.com`), phone formats |
| **Auto Scoring** | Computes scores using configurable negative marking schemes |
| **Leaderboard** | Ranked students per test with tiebreakers (score → accuracy → time) |
| **Flag & Recompute** | Manually flag suspicious attempts, recompute scores on demand |
| **Structured Logging** | Monolog-style JSON logs with `request_id` context propagation |
| **Interactive Dashboard** | React + Tailwind UI with filters, pagination, and drill-down |
| **Docker Ready** | One command to spin up the entire stack |

---

## Tech Stack

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                          │
│   React 18 · TypeScript · Vite · Tailwind CSS       │
│   Lucide Icons · Axios · React Router               │
├─────────────────────────────────────────────────────┤
│                    Backend                           │
│   Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic  │
│   Pydantic v2 · Structured JSON Logging             │
├─────────────────────────────────────────────────────┤
│                    Database                          │
│   PostgreSQL 16 · UUID PKs · JSONB · Enums          │
├─────────────────────────────────────────────────────┤
│                    DevOps                            │
│   Docker Compose · Nginx · Health Checks            │
└─────────────────────────────────────────────────────┘
```

---

## Getting Started

### Option 1: Docker (Recommended)

```bash
# Clone the repo
git clone https://github.com/abhi963007/assessment-ops-mini-platform.git
cd assessment-ops-mini-platform

# Start all services
docker-compose up --build

# 🎉 Open in browser:
#   Frontend → http://localhost:3000
#   API Docs → http://localhost:8000/docs
```

### Option 2: Local Development

<details>
<summary><b>Prerequisites</b></summary>

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+

</details>

<details>
<summary><b>1. Database Setup</b></summary>

```bash
# Create user and database
psql -U postgres -c "CREATE USER assessment WITH PASSWORD 'assessment123';"
psql -U postgres -c "CREATE DATABASE assessment_db OWNER assessment;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE assessment_db TO assessment;"
```

</details>

<details>
<summary><b>2. Backend</b></summary>

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate    # Linux/Mac
# venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export DATABASE_URL="postgresql://assessment:assessment123@localhost:5432/assessment_db"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

</details>

<details>
<summary><b>3. Frontend</b></summary>

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (auto-proxies /api → backend)
npm run dev

# 🎉 Open http://localhost:5173
```

</details>

<details>
<summary><b>4. Ingest the Dataset</b></summary>

```bash
# Using Python (from project root)
python -c "
import json, requests
events = json.load(open('attempt_events.json'))
r = requests.post('http://localhost:8000/api/ingest/attempts', json={'events': events})
data = r.json()
print(f'Ingested: {data[\"ingested\"]} | Duplicates: {data[\"duplicates\"]} | Errors: {data[\"errors\"]}')
"

# Or using curl
curl -X POST http://localhost:8000/api/ingest/attempts \
  -H "Content-Type: application/json" \
  -d "{\"events\": $(cat attempt_events.json)}"
```

</details>

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|:------:|----------|-------------|
| `POST` | `/api/ingest/attempts` | Ingest batch of attempt events |
| `GET` | `/api/attempts` | List attempts (filters + pagination) |
| `GET` | `/api/attempts/{id}` | Get attempt detail with score & flags |
| `GET` | `/api/attempts/{id}/duplicates` | Get duplicate thread (canonical + dups) |
| `POST` | `/api/attempts/{id}/recompute` | Recompute score for an attempt |
| `POST` | `/api/attempts/{id}/flag` | Flag an attempt with a reason |
| `GET` | `/api/leaderboard?test_id=...` | Ranked leaderboard for a test |
| `GET` | `/api/tests` | List all tests |
| `GET` | `/api/health` | Health check |

<details>
<summary><b>Attempt Filters (GET /api/attempts)</b></summary>

| Parameter | Type | Description |
|-----------|------|-------------|
| `test_id` | UUID | Filter by test |
| `student_id` | UUID | Filter by student |
| `status` | Enum | `INGESTED`, `DEDUPED`, `SCORED`, `FLAGGED` |
| `has_duplicates` | bool | Only show duplicates / non-duplicates |
| `search` | string | Search student name, email, or phone |
| `date_from` | ISO date | Filter by start date |
| `date_to` | ISO date | Filter by end date |
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20) |

</details>

<details>
<summary><b>Example: Ingest Request</b></summary>

```json
POST /api/ingest/attempts
{
  "events": [
    {
      "source_event_id": "evt_abc123",
      "student": {
        "full_name": "Anjali Kumar",
        "email": "a.njali.kumar+neet@gmail.com",
        "phone": "+91-98765 43210"
      },
      "test": {
        "name": "NEET Mock 1",
        "max_marks": 720,
        "negative_marking": { "correct": 4, "wrong": -1, "skip": 0 }
      },
      "started_at": "2026-01-15T10:00:00+05:30",
      "submitted_at": "2026-01-15T13:00:00+05:30",
      "answers": { "1": "A", "2": "B", "3": "SKIP", "4": "C" },
      "channel": "web"
    }
  ]
}
```

**Response:**
```json
{
  "ingested": 1,
  "duplicates": 0,
  "errors": 0,
  "results": [
    {
      "source_event_id": "evt_abc123",
      "attempt_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "SCORED",
      "message": "Ingested and scored successfully"
    }
  ]
}
```

</details>

---

## Architecture

### Data Flow

```
                    ┌──────────────┐
                    │  Raw Events  │  (messy JSON with duplicates)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Normalize  │  Gmail aliases, phone formats, names
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Deduplicate │  7-min window + 92% answer similarity
                    └──────┬───────┘
                           │
                ┌──────────┴──────────┐
                │                     │
         ┌──────▼───────┐     ┌──────▼───────┐
         │    Score      │     │  Mark Dedup  │
         │  (neg marks)  │     │   (link to   │
         │               │     │  canonical)  │
         └──────┬───────┘     └──────────────┘
                │
         ┌──────▼───────┐
         │   Store in   │
         │  PostgreSQL  │
         └──────┬───────┘
                │
     ┌──────────┴──────────┐
     │                     │
┌────▼─────┐        ┌─────▼────┐
│ REST API │        │ React UI │
│ (FastAPI)│◄───────│(Dashboard)│
└──────────┘        └──────────┘
```

### Database Schema

```
┌──────────────┐     ┌──────────────┐
│   students   │     │    tests     │
├──────────────┤     ├──────────────┤
│ id (UUID)    │     │ id (UUID)    │
│ full_name    │     │ name         │
│ email        │     │ max_marks    │
│ phone        │     │ neg_marking  │
│ norm_email   │     └──────┬───────┘
│ norm_phone   │            │
└──────┬───────┘            │
       │              ┌─────▼──────┐
       └──────────────► attempts   │
                      ├────────────┤
                      │ id (UUID)  │
                      │ student_id │──► students
                      │ test_id    │──► tests
                      │ answers    │  (JSONB)
                      │ status     │  (ENUM)
                      │ dup_of_id  │──► attempts (self-ref)
                      └─────┬──────┘
                            │
              ┌─────────────┼─────────────┐
              │                           │
       ┌──────▼───────┐           ┌──────▼───────┐
       │attempt_scores│           │    flags     │
       ├──────────────┤           ├──────────────┤
       │ attempt_id   │           │ id (UUID)    │
       │ correct      │           │ attempt_id   │
       │ wrong        │           │ reason       │
       │ skipped      │           │ created_at   │
       │ accuracy     │           └──────────────┘
       │ net_correct  │
       │ score        │
       │ explanation  │  (JSONB)
       └──────────────┘
```

---

## Project Structure

```
assessment-ops-mini-platform/
│
├── docker-compose.yml          # Full stack orchestration
├── .env.example                # Environment template
├── README.md                   # You are here!
├── DECISIONS.md                # Engineering decisions & assumptions
├── attempt_events.json         # Sample dataset (157 events)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   └── app/
│       ├── main.py             # FastAPI app + middleware
│       ├── config.py           # Pydantic settings
│       ├── database.py         # SQLAlchemy engine + session
│       ├── models.py           # ORM models
│       ├── schemas.py          # Pydantic request/response
│       ├── routes/
│       │   ├── ingest.py       # POST /api/ingest/attempts
│       │   ├── attempts.py     # CRUD + recompute + flag
│       │   └── leaderboard.py  # Rankings + /api/tests
│       └── services/
│           ├── normalize.py    # Email/phone/name normalization
│           ├── scoring.py      # Score computation engine
│           ├── dedup.py        # Deduplication logic
│           └── structured_log.py # Monolog-style JSON logger
│
└── frontend/
    ├── Dockerfile
    ├── nginx.conf              # Reverse proxy config
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── App.tsx             # Router + navigation
        ├── main.tsx            # Entry point
        ├── api/client.ts       # Axios API client + types
        └── pages/
            ├── AttemptsList.tsx # Filterable attempts table
            ├── AttemptDetail.tsx # Score breakdown + actions
            └── Leaderboard.tsx  # Ranked student table
```

---

## Design Decisions

> Full details in [`DECISIONS.md`](DECISIONS.md)

| Decision | Rationale |
|----------|-----------|
| **Gmail alias normalization** | Strip dots + `+alias` from local part to resolve student identity |
| **Phone: last 10 digits** | Handles `+91`, `0091`, spaces, dashes consistently |
| **7-min dedup window** | Accounts for re-submissions across channels (web, WhatsApp, email) |
| **92% answer similarity** | Allows ~6/75 (JEE) or ~14/180 (NEET) different answers |
| **No fuzzy matching libs** | Pure set-intersection similarity — fast, deterministic, no dependencies |
| **All non-SKIP = correct** | No answer key in dataset; `compute_score` accepts optional key for future use |
| **Structured JSON logging** | Every log line has `request_id`, `channel`, `context`, `extra` for debugging |
| **Best attempt per student** | Leaderboard uses highest score with tiebreakers |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://assessment:assessment123@localhost:5432/assessment_db` | PostgreSQL connection string |
| `LOG_LEVEL` | `INFO` | Logging level |
| `VITE_API_URL` | _(empty)_ | API base URL for frontend (uses proxy in dev) |

---

## License

This project is built as an assessment submission. Feel free to use it as a reference.

---

<div align="center">

**Built with** ❤️ **using FastAPI + React + PostgreSQL**

</div>
