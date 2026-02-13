import csv
import io
import json
import logging
import time
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student, Test, Attempt, AttemptScore, Flag
from app.schemas import AttemptEventPayload, IngestResponse, IngestResultItem
from app.routes.ingest import process_single_event
from app.services.structured_log import get_logger

router = APIRouter()
logger = get_logger('upload')


def parse_csv_to_events(content: str) -> list[dict]:
    """Convert CSV content to list of attempt event dicts."""
    reader = csv.DictReader(io.StringIO(content))
    events = []
    for i, row in enumerate(reader):
        event = {
            'source_event_id': row.get('source_event_id', f'csv_evt_{i}'),
            'student': {
                'full_name': row.get('full_name', row.get('student_name', '')),
                'email': row.get('email', row.get('student_email', None)),
                'phone': row.get('phone', row.get('student_phone', None)),
            },
            'test': {
                'name': row.get('test_name', row.get('test', 'Unknown Test')),
                'max_marks': int(row.get('max_marks', 300)),
                'negative_marking': json.loads(
                    row.get('negative_marking', '{"correct": 4, "wrong": -1, "skip": 0}')
                ),
            },
            'started_at': row.get('started_at', None),
            'submitted_at': row.get('submitted_at', None),
            'answers': {},
            'channel': row.get('channel', None),
        }
        # Collect answer columns (columns like "1", "2", "Q1", "q1", etc.)
        for key, val in row.items():
            if key and val:
                clean_key = key.strip().upper().replace('Q', '')
                if clean_key.isdigit():
                    event['answers'][clean_key] = val.strip().upper()
        events.append(event)
    return events


def analyze_events(events: list[dict]) -> dict:
    """Perform dynamic analysis on raw event data before ingestion."""
    total = len(events)
    if total == 0:
        return {'total_events': 0, 'message': 'No events found in file'}

    # Student analysis
    students = set()
    emails = set()
    phones = set()
    student_names = []

    # Test analysis
    test_names = Counter()
    test_max_marks = {}

    # Answer analysis
    total_answers = 0
    answer_distribution = Counter()
    questions_per_event = []
    skip_count = 0

    # Time analysis
    timestamps = []
    durations = []

    # Channel analysis
    channels = Counter()

    for evt in events:
        student = evt.get('student', {})
        name = student.get('full_name', 'Unknown')
        email = student.get('email')
        phone = student.get('phone')

        student_names.append(name)
        if email:
            emails.add(email.lower().strip())
        if phone:
            phones.add(phone.strip())
        students.add(f"{name}|{email}|{phone}")

        test = evt.get('test', {})
        test_name = test.get('name', 'Unknown')
        test_names[test_name] += 1
        if test_name not in test_max_marks:
            test_max_marks[test_name] = test.get('max_marks', 0)

        answers = evt.get('answers', {})
        num_q = len(answers)
        questions_per_event.append(num_q)
        total_answers += num_q

        for q, a in answers.items():
            answer_val = str(a).upper().strip()
            answer_distribution[answer_val] += 1
            if answer_val == 'SKIP':
                skip_count += 1

        channel = evt.get('channel')
        if channel:
            channels[channel] += 1

        started = evt.get('started_at')
        submitted = evt.get('submitted_at')
        if started:
            try:
                ts = started.strip()
                if ts.endswith('Z'):
                    ts = ts[:-1] + '+00:00'
                dt = datetime.fromisoformat(ts)
                timestamps.append(dt)
            except (ValueError, TypeError):
                pass

        if started and submitted:
            try:
                s_ts = started.strip()
                e_ts = submitted.strip()
                if s_ts.endswith('Z'):
                    s_ts = s_ts[:-1] + '+00:00'
                if e_ts.endswith('Z'):
                    e_ts = e_ts[:-1] + '+00:00'
                s_dt = datetime.fromisoformat(s_ts)
                e_dt = datetime.fromisoformat(e_ts)
                dur = (e_dt - s_dt).total_seconds() / 60
                if 0 < dur < 1440:
                    durations.append(round(dur, 1))
            except (ValueError, TypeError):
                pass

    # Compute stats
    unique_students = len(students)
    unique_emails = len(emails)
    unique_phones = len(phones)

    avg_questions = round(sum(questions_per_event) / total, 1) if total else 0
    avg_duration = round(sum(durations) / len(durations), 1) if durations else None
    min_duration = round(min(durations), 1) if durations else None
    max_duration = round(max(durations), 1) if durations else None

    # Answer type breakdown
    answered_count = total_answers - skip_count
    skip_rate = round((skip_count / total_answers) * 100, 1) if total_answers else 0

    # Date range
    date_range = None
    if timestamps:
        earliest = min(timestamps)
        latest = max(timestamps)
        date_range = {
            'earliest': earliest.isoformat(),
            'latest': latest.isoformat(),
            'span_days': (latest - earliest).days,
        }

    # Top answer choices (excluding SKIP)
    top_answers = [
        {'answer': ans, 'count': cnt}
        for ans, cnt in answer_distribution.most_common(10)
    ]

    # Tests breakdown
    tests_breakdown = [
        {'name': name, 'count': cnt, 'max_marks': test_max_marks.get(name, 0)}
        for name, cnt in test_names.most_common()
    ]

    # Potential duplicates (same student + test)
    student_test_pairs = Counter()
    for evt in events:
        student = evt.get('student', {})
        key = f"{student.get('email', '')}|{evt.get('test', {}).get('name', '')}"
        student_test_pairs[key] += 1
    potential_dups = sum(1 for v in student_test_pairs.values() if v > 1)

    return {
        'total_events': total,
        'unique_students': unique_students,
        'unique_emails': unique_emails,
        'unique_phones': unique_phones,
        'tests': tests_breakdown,
        'avg_questions_per_attempt': avg_questions,
        'total_answers': total_answers,
        'answered_count': answered_count,
        'skip_count': skip_count,
        'skip_rate_percent': skip_rate,
        'top_answers': top_answers,
        'channels': dict(channels) if channels else None,
        'duration_stats': {
            'avg_minutes': avg_duration,
            'min_minutes': min_duration,
            'max_minutes': max_duration,
            'sample_count': len(durations),
        } if durations else None,
        'date_range': date_range,
        'potential_duplicate_groups': potential_dups,
    }


@router.post('/api/upload/analyze')
async def upload_and_analyze(file: UploadFile = File(...)):
    """
    Upload a JSON or CSV file, analyze its contents dynamically,
    and return a rich analysis summary without ingesting.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail='No file provided')

    filename = file.filename.lower()
    content = await file.read()
    content_str = content.decode('utf-8-sig')  # Handle BOM

    try:
        if filename.endswith('.json'):
            raw = json.loads(content_str)
            # Support both array and {events: [...]} format
            if isinstance(raw, list):
                events = raw
            elif isinstance(raw, dict) and 'events' in raw:
                events = raw['events']
            else:
                raise HTTPException(
                    status_code=400,
                    detail='JSON must be an array of events or {events: [...]}',
                )
        elif filename.endswith('.csv'):
            events = parse_csv_to_events(content_str)
        else:
            raise HTTPException(
                status_code=400,
                detail='Unsupported file type. Please upload .json or .csv',
            )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f'Invalid JSON: {str(e)}')

    analysis = analyze_events(events)
    analysis['filename'] = file.filename
    analysis['file_size_kb'] = round(len(content) / 1024, 1)

    # Return events along with analysis for optional ingestion
    return {
        'analysis': analysis,
        'events': events,
    }


@router.post('/api/upload/ingest', response_model=IngestResponse)
async def upload_and_ingest(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a JSON or CSV file and ingest all events into the database.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail='No file provided')

    filename = file.filename.lower()
    content = await file.read()
    content_str = content.decode('utf-8-sig')

    try:
        if filename.endswith('.json'):
            raw = json.loads(content_str)
            if isinstance(raw, list):
                events = raw
            elif isinstance(raw, dict) and 'events' in raw:
                events = raw['events']
            else:
                raise HTTPException(
                    status_code=400,
                    detail='JSON must be an array of events or {events: [...]}',
                )
        elif filename.endswith('.csv'):
            events = parse_csv_to_events(content_str)
        else:
            raise HTTPException(
                status_code=400,
                detail='Unsupported file type. Please upload .json or .csv',
            )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f'Invalid JSON: {str(e)}')

    start_time = time.time()

    logger.log_with_data(
        logging.INFO,
        f'File upload ingestion started: {file.filename} ({len(events)} events)',
    )

    results: list[IngestResultItem] = []
    ingested = 0
    duplicates = 0
    errors = 0
    skipped = 0
    warnings = 0

    for event_data in events:
        try:
            event = AttemptEventPayload(**event_data)
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
                source_event_id=event_data.get('source_event_id', 'unknown'),
                status='ERROR',
                message=str(e),
            ))

    db.commit()

    duration_ms = round((time.time() - start_time) * 1000, 2)

    logger.log_with_data(
        logging.INFO,
        f'File ingestion complete: {ingested} ingested, {duplicates} duplicates, '
        f'{skipped} skipped, {warnings} warnings, {errors} errors ({duration_ms}ms)',
    )

    return IngestResponse(
        ingested=ingested,
        duplicates=duplicates,
        errors=errors,
        skipped=skipped,
        warnings=warnings,
        results=results,
    )


@router.get('/api/data/stats')
def get_stats(db: Session = Depends(get_db)):
    """Get database statistics for dashboard."""
    from sqlalchemy import func
    total_attempts = db.query(func.count(Attempt.id)).scalar() or 0
    total_students = db.query(func.count(Student.id)).scalar() or 0
    total_tests = db.query(func.count(Test.id)).scalar() or 0
    scored = db.query(func.count(Attempt.id)).filter(Attempt.status == 'SCORED').scalar() or 0
    deduped = db.query(func.count(Attempt.id)).filter(Attempt.status == 'DEDUPED').scalar() or 0
    flagged = db.query(func.count(Attempt.id)).filter(Attempt.status == 'FLAGGED').scalar() or 0
    return {
        'total_attempts': total_attempts,
        'total_students': total_students,
        'total_tests': total_tests,
        'scored': scored,
        'deduped': deduped,
        'flagged': flagged,
        'has_data': total_attempts > 0,
    }


@router.post('/api/data/reset')
def reset_database(db: Session = Depends(get_db)):
    """
    Clear all ingested data for a fresh import.
    Deletes: flags, scores, attempts, students, tests.
    """
    try:
        db.query(Flag).delete()
        db.query(AttemptScore).delete()
        db.query(Attempt).delete()
        db.query(Student).delete()
        db.query(Test).delete()
        db.commit()

        logger.log_with_data(logging.INFO, 'Database reset: all data cleared')

        return {'status': 'ok', 'message': 'All data cleared successfully'}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Reset failed: {str(e)}')
