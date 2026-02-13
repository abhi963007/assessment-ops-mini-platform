from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Ingest request schemas ---

class StudentPayload(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class TestPayload(BaseModel):
    name: str
    max_marks: int
    negative_marking: dict


class AttemptEventPayload(BaseModel):
    source_event_id: str
    student: StudentPayload
    test: TestPayload
    started_at: Optional[str] = None
    submitted_at: Optional[str] = None
    answers: dict[str, str] = Field(default_factory=dict)
    channel: Optional[str] = None


class IngestRequest(BaseModel):
    events: list[AttemptEventPayload]


# --- Response schemas ---

class StudentResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TestResponse(BaseModel):
    id: uuid.UUID
    name: str
    max_marks: int
    negative_marking: dict
    created_at: datetime

    class Config:
        from_attributes = True


class AttemptScoreResponse(BaseModel):
    attempt_id: uuid.UUID
    correct: int
    wrong: int
    skipped: int
    accuracy: float
    net_correct: int
    score: float
    computed_at: datetime
    explanation: Optional[dict] = None

    class Config:
        from_attributes = True


class FlagResponse(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    reason: str
    created_at: datetime

    class Config:
        from_attributes = True


class AttemptResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    test_id: uuid.UUID
    source_event_id: str
    started_at: datetime
    submitted_at: Optional[datetime] = None
    answers: dict
    status: str
    duplicate_of_attempt_id: Optional[uuid.UUID] = None
    student: Optional[StudentResponse] = None
    test: Optional[TestResponse] = None
    score: Optional[AttemptScoreResponse] = None
    flags: list[FlagResponse] = []

    class Config:
        from_attributes = True


class AttemptListResponse(BaseModel):
    items: list[AttemptResponse]
    total: int
    page: int
    page_size: int


class IngestResultItem(BaseModel):
    source_event_id: str
    attempt_id: Optional[uuid.UUID] = None
    status: str
    message: str


class IngestResponse(BaseModel):
    ingested: int
    duplicates: int
    errors: int
    results: list[IngestResultItem]


class FlagRequest(BaseModel):
    reason: str


class LeaderboardEntry(BaseModel):
    rank: int
    student_id: uuid.UUID
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    attempt_id: uuid.UUID
    score: float
    accuracy: float
    net_correct: int
    correct: int
    wrong: int
    skipped: int
    submitted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    test_id: uuid.UUID
    test_name: str
    entries: list[LeaderboardEntry]
