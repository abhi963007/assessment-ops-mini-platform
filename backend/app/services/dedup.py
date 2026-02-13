import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Attempt
from app.services.structured_log import get_logger

logger = get_logger('dedup')

# Dedup thresholds
TIME_WINDOW_MINUTES = 7
SIMILARITY_THRESHOLD = 0.92


def compute_answer_similarity(answers_a: dict, answers_b: dict) -> float:
    """
    Compute similarity between two answer sets.
    similarity = matching_answers / total_compared_questions

    Only compares questions present in BOTH answer sets.
    """
    common_keys = set(answers_a.keys()) & set(answers_b.keys())

    if not common_keys:
        return 0.0

    matching = sum(
        1 for k in common_keys
        if answers_a[k] == answers_b[k]
    )

    return matching / len(common_keys)


def find_duplicate(
    db: Session,
    student_id: str,
    test_id: str,
    started_at: datetime,
    answers: dict,
) -> Optional[Attempt]:
    """
    Check if an attempt is a duplicate of an existing one.

    Dedup rules:
    1. Same student
    2. Same test
    3. started_at within 7 minutes
    4. Answer similarity >= 0.92

    Returns the canonical (earliest) attempt if duplicate found, else None.
    """
    time_lower = started_at - timedelta(minutes=TIME_WINDOW_MINUTES)
    time_upper = started_at + timedelta(minutes=TIME_WINDOW_MINUTES)

    # Find candidate attempts: same student, same test, within time window
    candidates = db.query(Attempt).filter(
        Attempt.student_id == student_id,
        Attempt.test_id == test_id,
        Attempt.started_at >= time_lower,
        Attempt.started_at <= time_upper,
        Attempt.status != 'DEDUPED',  # Don't compare against already-deduped
    ).order_by(Attempt.started_at.asc()).all()

    for candidate in candidates:
        similarity = compute_answer_similarity(answers, candidate.answers)

        logger.log_with_data(
            logging.DEBUG,
            f'Dedup comparison: similarity={similarity:.4f} '
            f'(threshold={SIMILARITY_THRESHOLD})',
            attempt_id=str(candidate.id),
            student_id=str(student_id),
            extra_data={
                'candidate_id': str(candidate.id),
                'similarity': round(similarity, 4),
                'threshold': SIMILARITY_THRESHOLD,
                'time_diff_seconds': abs(
                    (started_at - candidate.started_at).total_seconds()
                ),
            },
        )

        if similarity >= SIMILARITY_THRESHOLD:
            # Find the canonical attempt (earliest in the chain)
            canonical = candidate
            while canonical.duplicate_of_attempt_id:
                parent = db.query(Attempt).get(canonical.duplicate_of_attempt_id)
                if parent:
                    canonical = parent
                else:
                    break

            logger.log_with_data(
                logging.INFO,
                f'Duplicate found: canonical={canonical.id}, similarity={similarity:.4f}',
                attempt_id=str(candidate.id),
                student_id=str(student_id),
                extra_data={
                    'canonical_id': str(canonical.id),
                    'similarity': round(similarity, 4),
                },
            )

            return canonical

    return None
