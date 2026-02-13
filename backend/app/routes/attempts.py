import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Attempt, AttemptScore, Flag
from app.schemas import (
    AttemptResponse, AttemptListResponse, FlagRequest, FlagResponse,
    AttemptScoreResponse,
)
from app.services.scoring import compute_score
from app.services.structured_log import get_logger

router = APIRouter()
logger = get_logger('http')


@router.get('/api/attempts', response_model=AttemptListResponse)
def list_attempts(
    test_id: Optional[UUID] = Query(None),
    student_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    has_duplicates: Optional[bool] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List attempts with filters and pagination."""
    query = db.query(Attempt).options(
        joinedload(Attempt.student),
        joinedload(Attempt.test),
        joinedload(Attempt.score),
        joinedload(Attempt.flags),
    )

    if test_id:
        query = query.filter(Attempt.test_id == test_id)
    if student_id:
        query = query.filter(Attempt.student_id == student_id)
    if status:
        query = query.filter(Attempt.status == status)
    if has_duplicates is True:
        query = query.filter(Attempt.duplicate_of_attempt_id.isnot(None))
    elif has_duplicates is False:
        query = query.filter(Attempt.duplicate_of_attempt_id.is_(None))

    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Attempt.started_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Attempt.started_at <= dt_to)
        except ValueError:
            pass

    if search:
        from app.models import Student
        query = query.join(Student).filter(
            Student.full_name.ilike(f'%{search}%')
            | Student.email.ilike(f'%{search}%')
            | Student.phone.ilike(f'%{search}%')
        )

    total = query.count()
    items = (
        query
        .order_by(Attempt.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    logger.log_with_data(
        logging.INFO,
        f'Listed attempts: {len(items)} of {total}',
        extra_data={'page': page, 'page_size': page_size, 'total': total},
    )

    return AttemptListResponse(
        items=[AttemptResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get('/api/attempts/{attempt_id}', response_model=AttemptResponse)
def get_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a single attempt with full details."""
    attempt = db.query(Attempt).options(
        joinedload(Attempt.student),
        joinedload(Attempt.test),
        joinedload(Attempt.score),
        joinedload(Attempt.flags),
    ).filter(Attempt.id == attempt_id).first()

    if not attempt:
        raise HTTPException(status_code=404, detail='Attempt not found')

    return AttemptResponse.model_validate(attempt)


@router.post('/api/attempts/{attempt_id}/recompute', response_model=AttemptScoreResponse)
def recompute_score(
    attempt_id: UUID,
    db: Session = Depends(get_db),
):
    """Recalculate score for an attempt."""
    attempt = db.query(Attempt).options(
        joinedload(Attempt.test),
    ).filter(Attempt.id == attempt_id).first()

    if not attempt:
        raise HTTPException(status_code=404, detail='Attempt not found')

    score = compute_score(db, attempt)
    if attempt.status not in ('FLAGGED',):
        attempt.status = 'SCORED'
    db.commit()
    db.refresh(score)

    logger.log_with_data(
        logging.INFO,
        f'Score recomputed for attempt {attempt_id}',
        attempt_id=str(attempt_id),
    )

    return AttemptScoreResponse.model_validate(score)


@router.post('/api/attempts/{attempt_id}/flag', response_model=FlagResponse)
def flag_attempt(
    attempt_id: UUID,
    request: FlagRequest,
    db: Session = Depends(get_db),
):
    """Flag an attempt with a reason."""
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()

    if not attempt:
        raise HTTPException(status_code=404, detail='Attempt not found')

    flag = Flag(
        attempt_id=attempt.id,
        reason=request.reason,
    )
    db.add(flag)
    attempt.status = 'FLAGGED'
    db.commit()
    db.refresh(flag)

    logger.log_with_data(
        logging.INFO,
        f'Attempt {attempt_id} flagged: {request.reason}',
        attempt_id=str(attempt_id),
    )

    return FlagResponse.model_validate(flag)


@router.get('/api/attempts/{attempt_id}/duplicates')
def get_duplicate_thread(
    attempt_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the duplicate thread for an attempt (canonical + all duplicates)."""
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail='Attempt not found')

    # Find canonical
    canonical = attempt
    while canonical.duplicate_of_attempt_id:
        parent = db.query(Attempt).get(canonical.duplicate_of_attempt_id)
        if parent:
            canonical = parent
        else:
            break

    # Find all duplicates pointing to canonical
    duplicates = db.query(Attempt).options(
        joinedload(Attempt.student),
        joinedload(Attempt.score),
    ).filter(
        Attempt.duplicate_of_attempt_id == canonical.id
    ).all()

    # Load canonical with relations
    canonical = db.query(Attempt).options(
        joinedload(Attempt.student),
        joinedload(Attempt.score),
    ).filter(Attempt.id == canonical.id).first()

    return {
        'canonical': AttemptResponse.model_validate(canonical),
        'duplicates': [AttemptResponse.model_validate(d) for d in duplicates],
    }
