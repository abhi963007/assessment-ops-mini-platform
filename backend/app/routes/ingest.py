import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student, Test, Attempt
from app.schemas import (
    AttemptEventPayload, IngestRequest, IngestResponse, IngestResultItem,
)
from app.services.normalize import (
    normalize_email, normalize_phone, normalize_name, get_student_identity,
)
from app.services.dedup import find_duplicate
from app.services.scoring import compute_score
from app.services.structured_log import get_logger

router = APIRouter()
logger = get_logger('http')
db_logger = get_logger('db')
dedup_logger = get_logger('dedup')


def parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp string, handling common malformations."""
    if not ts:
        return None
    try:
        # Handle 'Z' suffix
        cleaned = ts.strip()
        if cleaned.endswith('Z'):
            cleaned = cleaned[:-1] + '+00:00'
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def find_or_create_student(
    db: Session,
    payload: AttemptEventPayload,
) -> Student:
    """Find existing student by normalized identity, or create new one."""
    norm_email = normalize_email(payload.student.email)
    norm_phone = normalize_phone(payload.student.phone)

    # Search by normalized email first, then phone
    student = None
    if norm_email:
        student = db.query(Student).filter(
            Student.normalized_email == norm_email
        ).first()

    if not student and norm_phone:
        student = db.query(Student).filter(
            Student.normalized_phone == norm_phone
        ).first()

    if student:
        # Update name if current one looks more complete
        new_name = normalize_name(payload.student.full_name)
        if len(new_name) > len(student.full_name):
            student.full_name = new_name
        # Fill in missing contact info
        if not student.email and payload.student.email:
            student.email = payload.student.email.strip()
        if not student.phone and payload.student.phone:
            student.phone = payload.student.phone.strip()
        if not student.normalized_email and norm_email:
            student.normalized_email = norm_email
        if not student.normalized_phone and norm_phone:
            student.normalized_phone = norm_phone

        db_logger.log_with_data(
            logging.DEBUG,
            f'Found existing student: {student.id}',
            student_id=str(student.id),
        )
        return student

    # Create new student
    student = Student(
        full_name=normalize_name(payload.student.full_name),
        email=payload.student.email.strip() if payload.student.email else None,
        phone=payload.student.phone.strip() if payload.student.phone else None,
        normalized_email=norm_email,
        normalized_phone=norm_phone,
    )
    db.add(student)
    db.flush()

    db_logger.log_with_data(
        logging.INFO,
        f'Created new student: {student.full_name}',
        student_id=str(student.id),
    )
    return student


def find_or_create_test(db: Session, payload: AttemptEventPayload) -> Test:
    """Find existing test by name, or create new one."""
    test = db.query(Test).filter(Test.name == payload.test.name).first()

    if test:
        return test

    test = Test(
        name=payload.test.name,
        max_marks=payload.test.max_marks,
        negative_marking=payload.test.negative_marking,
    )
    db.add(test)
    db.flush()

    db_logger.log_with_data(
        logging.INFO,
        f'Created new test: {test.name}',
        extra_data={'test_id': str(test.id)},
    )
    return test


def process_single_event(
    db: Session,
    event: AttemptEventPayload,
) -> IngestResultItem:
    """Process a single attempt event: validate, store, dedup, score."""
    raw_payload = event.model_dump()

    # Skip if source_event_id already exists in DB
    existing = db.query(Attempt).filter(
        Attempt.source_event_id == event.source_event_id
    ).first()
    if existing:
        return IngestResultItem(
            source_event_id=event.source_event_id,
            attempt_id=existing.id,
            status='SKIPPED',
            message=f'Already ingested (attempt {existing.id})',
        )

    # Validate: must have at least email or phone
    if not event.student.email and not event.student.phone:
        return IngestResultItem(
            source_event_id=event.source_event_id,
            status='ERROR',
            message='Student must have at least an email or phone',
        )

    # Parse timestamps
    started_at = parse_timestamp(event.started_at)
    if not started_at:
        return IngestResultItem(
            source_event_id=event.source_event_id,
            status='WARNING',
            message=f'Skipped: malformed timestamp ({event.started_at})',
        )

    submitted_at = parse_timestamp(event.submitted_at)

    # Find or create student and test
    student = find_or_create_student(db, event)
    test = find_or_create_test(db, event)

    # Create attempt record
    attempt = Attempt(
        student_id=student.id,
        test_id=test.id,
        source_event_id=event.source_event_id,
        started_at=started_at,
        submitted_at=submitted_at,
        answers=event.answers,
        raw_payload=raw_payload,
        status='INGESTED',
    )
    db.add(attempt)
    db.flush()

    logger.log_with_data(
        logging.INFO,
        f'Attempt ingested: {attempt.id}',
        attempt_id=str(attempt.id),
        student_id=str(student.id),
    )

    # Check for duplicates
    canonical = find_duplicate(
        db,
        student_id=str(student.id),
        test_id=str(test.id),
        started_at=started_at,
        answers=event.answers,
    )

    if canonical and canonical.id != attempt.id:
        attempt.status = 'DEDUPED'
        attempt.duplicate_of_attempt_id = canonical.id

        dedup_logger.log_with_data(
            logging.INFO,
            f'Attempt {attempt.id} marked as duplicate of {canonical.id}',
            attempt_id=str(attempt.id),
            student_id=str(student.id),
            extra_data={'canonical_id': str(canonical.id)},
        )

        return IngestResultItem(
            source_event_id=event.source_event_id,
            attempt_id=attempt.id,
            status='DEDUPED',
            message=f'Duplicate of attempt {canonical.id}',
        )

    # Score the attempt
    compute_score(db, attempt)
    attempt.status = 'SCORED'

    return IngestResultItem(
        source_event_id=event.source_event_id,
        attempt_id=attempt.id,
        status='SCORED',
        message='Ingested and scored successfully',
    )


@router.post('/api/ingest/attempts', response_model=IngestResponse)
def ingest_attempts(
    request: IngestRequest,
    db: Session = Depends(get_db),
):
    """
    Ingest a batch of attempt events.
    Validates, stores, deduplicates, and scores each event.
    """
    start_time = time.time()

    logger.log_with_data(
        logging.INFO,
        f'Ingestion started: {len(request.events)} events',
        extra_data={'event_count': len(request.events)},
    )

    results: list[IngestResultItem] = []
    ingested = 0
    duplicates = 0
    errors = 0
    skipped = 0
    warnings = 0

    for event in request.events:
        try:
            result = process_single_event(db, event)
            results.append(result)

            if result.status == 'SCORED':
                ingested += 1
            elif result.status == 'DEDUPED':
                duplicates += 1
            elif result.status == 'SKIPPED':
                skipped += 1
            elif result.status == 'WARNING':
                warnings += 1
            else:
                errors += 1
        except Exception as e:
            db.rollback()
            errors += 1
            results.append(IngestResultItem(
                source_event_id=event.source_event_id,
                status='ERROR',
                message=str(e),
            ))
            logger.log_with_data(
                logging.ERROR,
                f'Error processing event {event.source_event_id}: {e}',
                extra_data={'error': str(e)},
            )

    db.commit()

    duration_ms = round((time.time() - start_time) * 1000, 2)

    logger.log_with_data(
        logging.INFO,
        f'Ingestion complete: {ingested} ingested, {duplicates} duplicates, {errors} errors',
        extra_data={
            'ingested': ingested,
            'duplicates': duplicates,
            'errors': errors,
            'duration_ms': duration_ms,
        },
    )

    return IngestResponse(
        ingested=ingested,
        duplicates=duplicates,
        errors=errors,
        skipped=skipped,
        warnings=warnings,
        results=results,
    )
