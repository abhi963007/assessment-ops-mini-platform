import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Attempt, AttemptScore
from app.services.structured_log import get_logger

logger = get_logger('scoring')


def compute_score(
    db: Session,
    attempt: Attempt,
    answer_key: Optional[dict] = None,
) -> AttemptScore:
    """
    Compute score for an attempt using the test's negative_marking config.

    Since we don't have an answer key in the dataset, we count answers
    as: answered (A/B/C/D) vs SKIP. Without an answer key, we treat
    all non-SKIP answers as "correct" for demonstration — but the real
    implementation would compare against an answer key.

    For this assignment: we score based on the answer distribution:
    - correct = count of non-SKIP answers (or matched answers if key provided)
    - wrong = 0 (or mismatched answers if key provided)
    - skipped = count of SKIP answers
    """
    start_time = time.time()

    answers = attempt.answers or {}
    neg_marking = attempt.test.negative_marking

    correct_pts = neg_marking.get('correct', 4)
    wrong_pts = neg_marking.get('wrong', -1)
    skip_pts = neg_marking.get('skip', 0)

    correct_count = 0
    wrong_count = 0
    skipped_count = 0

    for q_no, answer in answers.items():
        if answer == 'SKIP':
            skipped_count += 1
        elif answer_key and q_no in answer_key:
            if answer == answer_key[q_no]:
                correct_count += 1
            else:
                wrong_count += 1
        else:
            # No answer key: count all non-SKIP as answered
            # We'll treat them as correct for scoring purposes
            correct_count += 1

    total_answered = correct_count + wrong_count
    accuracy = (correct_count / total_answered * 100) if total_answered > 0 else 0.0
    net_correct = correct_count - wrong_count
    score = (correct_count * correct_pts) + (wrong_count * wrong_pts) + (skipped_count * skip_pts)

    explanation = {
        'marking_scheme': {
            'correct': correct_pts,
            'wrong': wrong_pts,
            'skip': skip_pts,
        },
        'counts': {
            'correct': correct_count,
            'wrong': wrong_count,
            'skipped': skipped_count,
            'total_questions': len(answers),
        },
        'formula': f'({correct_count} × {correct_pts}) + ({wrong_count} × {wrong_pts}) + ({skipped_count} × {skip_pts}) = {score}',
        'answer_key_used': answer_key is not None,
    }

    # Upsert score
    existing = db.query(AttemptScore).filter(
        AttemptScore.attempt_id == attempt.id
    ).first()

    if existing:
        existing.correct = correct_count
        existing.wrong = wrong_count
        existing.skipped = skipped_count
        existing.accuracy = round(accuracy, 2)
        existing.net_correct = net_correct
        existing.score = round(score, 2)
        existing.computed_at = datetime.now(timezone.utc)
        existing.explanation = explanation
        attempt_score = existing
    else:
        attempt_score = AttemptScore(
            attempt_id=attempt.id,
            correct=correct_count,
            wrong=wrong_count,
            skipped=skipped_count,
            accuracy=round(accuracy, 2),
            net_correct=net_correct,
            score=round(score, 2),
            computed_at=datetime.now(timezone.utc),
            explanation=explanation,
        )
        db.add(attempt_score)

    duration_ms = round((time.time() - start_time) * 1000, 2)

    logger.log_with_data(
        logging.INFO,
        f'Score computed: {score} (correct={correct_count}, wrong={wrong_count}, skip={skipped_count})',
        attempt_id=str(attempt.id),
        student_id=str(attempt.student_id),
        extra_data={
            'score': float(score),
            'accuracy': round(accuracy, 2),
            'duration_ms': duration_ms,
        },
    )

    return attempt_score
