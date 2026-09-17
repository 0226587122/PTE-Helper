"""Keeping the active question pool topped up from backups."""

import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Question, QuestionReport, User, utc_now

log = logging.getLogger(__name__)


def _now() -> datetime:
    return utc_now()


def active_count(db: Session, code: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Question).where(Question.task_type_code == code, Question.status == "active")
    ) or 0


def promote_backup(db: Session, code: str, question_id: int | None = None) -> Question | None:
    """Promote a specific backup question, or the oldest backup of that type when no id is given."""
    query = select(Question).where(Question.task_type_code == code, Question.status == "backup")
    if question_id is not None:
        query = query.where(Question.id == question_id)
    query = query.order_by(Question.created_at, Question.id).limit(1).with_for_update()
    question = db.scalars(query).first()
    if question is None:
        return None
    question.status = "active"
    question.promoted_at = _now()
    log.info("Promoted backup question %s (%s) to active", question.id, code)
    return question


def top_up_active(db: Session, code: str) -> list[Question]:
    """Promote the oldest backups until the type has MIN_ACTIVE_PER_TYPE active questions (or backups run out)."""
    minimum = get_settings().min_active_per_type
    promoted: list[Question] = []
    db.flush()
    count = active_count(db, code)
    while count < minimum:
        question = promote_backup(db, code)
        if question is None:
            log.warning("%s has %s active questions and no backups left to promote", code, count)
            break
        db.flush()
        promoted.append(question)
        count += 1
    return promoted


def retire_question(db: Session, question: Question) -> list[Question]:
    if question.status != "retired":
        question.status = "retired"
        question.retired_at = _now()
    return top_up_active(db, question.task_type_code)


def set_status(db: Session, question: Question, status: str) -> list[Question]:
    """Change a question's status. Retiring (or demoting) an active question triggers backup promotion."""
    if status == "retired":
        return retire_question(db, question)
    question.status = status
    if status == "active":
        question.retired_at = None
        question.promoted_at = _now()
    return top_up_active(db, question.task_type_code)


def open_report_count(db: Session, question_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(QuestionReport)
        .where(QuestionReport.question_id == question_id, QuestionReport.resolved_at.is_(None))
    ) or 0


def report_question(db: Session, question: Question, user: User, reason: str) -> tuple[QuestionReport, bool]:
    """Record a report. Returns the report and whether the question was retired because of it."""
    report = QuestionReport(question_id=question.id, user_id=user.id, reason=reason)
    db.add(report)
    question.report_count += 1
    db.flush()
    retired = False
    if question.status != "retired" and open_report_count(db, question.id) >= get_settings().report_retire_threshold:
        retire_question(db, question)
        retired = True
    return report, retired
