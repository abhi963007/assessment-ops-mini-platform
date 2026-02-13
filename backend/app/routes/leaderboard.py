import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attempt, AttemptScore, Student, Test
from app.schemas import LeaderboardEntry, LeaderboardResponse
from app.services.structured_log import get_logger

router = APIRouter()
logger = get_logger('http')


@router.get('/api/leaderboard', response_model=LeaderboardResponse)
def get_leaderboard(
    test_id: UUID = Query(..., description='Test ID to get leaderboard for'),
    db: Session = Depends(get_db),
):
    """
    Get ranked leaderboard for a test.
    Uses best attempt per student (highest score).
    Tiebreakers: accuracy > net_correct > earliest submission.
    """
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail='Test not found')

    # Subquery: best score per student for this test (non-deduped attempts only)
    best_score_subq = (
        db.query(
            Attempt.student_id,
            func.max(AttemptScore.score).label('max_score'),
        )
        .join(AttemptScore, AttemptScore.attempt_id == Attempt.id)
        .filter(
            Attempt.test_id == test_id,
            Attempt.status.in_(['SCORED', 'FLAGGED']),
        )
        .group_by(Attempt.student_id)
        .subquery()
    )

    # Main query: get the actual attempt rows matching best score
    results = (
        db.query(
            Student,
            Attempt,
            AttemptScore,
        )
        .join(Attempt, Attempt.student_id == Student.id)
        .join(AttemptScore, AttemptScore.attempt_id == Attempt.id)
        .join(
            best_score_subq,
            and_(
                Attempt.student_id == best_score_subq.c.student_id,
                AttemptScore.score == best_score_subq.c.max_score,
            ),
        )
        .filter(
            Attempt.test_id == test_id,
            Attempt.status.in_(['SCORED', 'FLAGGED']),
        )
        .order_by(
            AttemptScore.score.desc(),
            AttemptScore.accuracy.desc(),
            AttemptScore.net_correct.desc(),
            func.coalesce(Attempt.submitted_at, Attempt.started_at).asc(),
        )
        .all()
    )

    # Deduplicate: keep only first (best) row per student
    seen_students = set()
    entries = []
    rank = 0

    for student, attempt, score in results:
        if student.id in seen_students:
            continue
        seen_students.add(student.id)
        rank += 1

        entries.append(LeaderboardEntry(
            rank=rank,
            student_id=student.id,
            full_name=student.full_name,
            email=student.email,
            phone=student.phone,
            attempt_id=attempt.id,
            score=float(score.score),
            accuracy=float(score.accuracy),
            net_correct=score.net_correct,
            correct=score.correct,
            wrong=score.wrong,
            skipped=score.skipped,
            submitted_at=attempt.submitted_at or attempt.started_at,
        ))

    logger.log_with_data(
        logging.INFO,
        f'Leaderboard generated for test {test.name}: {len(entries)} students',
        extra_data={'test_id': str(test_id), 'entries': len(entries)},
    )

    return LeaderboardResponse(
        test_id=test.id,
        test_name=test.name,
        entries=entries,
    )


@router.get('/api/tests')
def list_tests(db: Session = Depends(get_db)):
    """List all tests."""
    tests = db.query(Test).order_by(Test.name).all()
    return [
        {
            'id': str(t.id),
            'name': t.name,
            'max_marks': t.max_marks,
            'negative_marking': t.negative_marking,
        }
        for t in tests
    ]
