import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Numeric, Text, ForeignKey,
    DateTime, Enum as SAEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = 'students'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(Text, nullable=False)
    email = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    normalized_email = Column(Text, nullable=True, index=True)
    normalized_phone = Column(Text, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    attempts = relationship('Attempt', back_populates='student')


class Test(Base):
    __tablename__ = 'tests'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    max_marks = Column(Integer, nullable=False)
    negative_marking = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    attempts = relationship('Attempt', back_populates='test')


class Attempt(Base):
    __tablename__ = 'attempts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey('students.id'), nullable=False)
    test_id = Column(UUID(as_uuid=True), ForeignKey('tests.id'), nullable=False)
    source_event_id = Column(Text, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    answers = Column(JSONB, nullable=False, default=dict)
    raw_payload = Column(JSONB, nullable=False)
    status = Column(
        SAEnum('INGESTED', 'DEDUPED', 'SCORED', 'FLAGGED', name='attempt_status'),
        nullable=False,
        default='INGESTED'
    )
    duplicate_of_attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey('attempts.id'),
        nullable=True
    )

    student = relationship('Student', back_populates='attempts')
    test = relationship('Test', back_populates='attempts')
    score = relationship('AttemptScore', back_populates='attempt', uselist=False)
    flags = relationship('Flag', back_populates='attempt')
    canonical_attempt = relationship('Attempt', remote_side='Attempt.id')

    __table_args__ = (
        Index('ix_attempts_student_test', 'student_id', 'test_id'),
        Index('ix_attempts_status', 'status'),
        Index('ix_attempts_started_at', 'started_at'),
    )


class AttemptScore(Base):
    __tablename__ = 'attempt_scores'

    attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey('attempts.id'),
        primary_key=True
    )
    correct = Column(Integer, nullable=False, default=0)
    wrong = Column(Integer, nullable=False, default=0)
    skipped = Column(Integer, nullable=False, default=0)
    accuracy = Column(Numeric(7, 2), nullable=False, default=0)
    net_correct = Column(Integer, nullable=False, default=0)
    score = Column(Numeric(10, 2), nullable=False, default=0)
    computed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    explanation = Column(JSONB, nullable=True)

    attempt = relationship('Attempt', back_populates='score')


class Flag(Base):
    __tablename__ = 'flags'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey('attempts.id'), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    attempt = relationship('Attempt', back_populates='flags')
