"""Drawing a randomised practice set."""

import logging
import random
import secrets

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ContentSource, PracticeSet, Question, QuestionReport, SetQuestion, User
from app.task_types import TYPES_BY_CODE
from app.variants import SourceData, render

log = logging.getLogger(__name__)


def source_data(source: ContentSource | None) -> SourceData | None:
    if source is None:
        return None
    return SourceData(
        source_key=source.source_key,
        kind=source.kind,
        title=source.title,
        body=source.body,
        blank_markup=source.blank_markup,
        turns=source.turns,
    )


def recent_question_ids(db: Session, user_id: int, code: str, set_limit: int) -> set[int]:
    """Questions of this type the student met in their last few sets, drills and mock tests alike."""
    if set_limit <= 0:
        return set()
    recent_sets = (
        select(PracticeSet.id)
        .join(SetQuestion, SetQuestion.set_id == PracticeSet.id)
        .where(PracticeSet.user_id == user_id, SetQuestion.task_type_code == code)
        .group_by(PracticeSet.id)
        .order_by(func.max(PracticeSet.started_at).desc(), PracticeSet.id.desc())
        .limit(set_limit)
    )
    set_ids = list(db.scalars(recent_sets))
    if not set_ids:
        return set()
    return set(
        db.scalars(
            select(SetQuestion.question_id).where(
                SetQuestion.set_id.in_(set_ids), SetQuestion.task_type_code == code
            )
        )
    )


def _random_ids(
    db: Session,
    code: str,
    status: str,
    exclude: set[int],
    limit: int,
    exclude_sources: set[int] | None = None,
) -> list[int]:
    """Random ids from a filtered id list. ORDER BY RAND() only ever runs over this type's matching ids."""
    if limit <= 0:
        return []
    open_reports = select(QuestionReport.question_id).where(QuestionReport.resolved_at.is_(None))
    query = (
        select(Question.id)
        .where(
            Question.task_type_code == code,
            Question.status == status,
            Question.id.not_in(open_reports),
        )
    )
    if exclude:
        query = query.where(Question.id.not_in(exclude))
    if exclude_sources:
        # Keeps one lecture or passage from turning up twice in the same mock test.
        query = query.where(or_(Question.source_id.is_(None), Question.source_id.not_in(exclude_sources)))
    query = query.order_by(func.rand()).limit(limit)
    return list(db.scalars(query))


def pick_question_ids(
    db: Session, user_id: int, code: str, count: int, exclude_sources: set[int] | None = None
) -> list[tuple[int, bool]]:
    """Returns (question_id, drew_from_backup) pairs."""
    settings = get_settings()
    recent = recent_question_ids(db, user_id, code, settings.recent_sets_excluded)

    picked: list[tuple[int, bool]] = [
        (qid, False) for qid in _random_ids(db, code, "active", recent, count, exclude_sources)
    ]
    if len(picked) < count:
        chosen = recent | {qid for qid, _ in picked}
        picked += [
            (qid, True) for qid in _random_ids(db, code, "backup", chosen, count - len(picked), exclude_sources)
        ]

    if len(picked) < count:
        log.warning(
            "Not enough fresh questions for user %s on %s (%s of %s); allowing repeats",
            user_id, code, len(picked), count,
        )
        chosen = {qid for qid, _ in picked}
        for status, from_backup in (("active", False), ("backup", True)):
            extra = _random_ids(db, code, status, chosen, count - len(picked), exclude_sources)
            picked += [(qid, from_backup) for qid in extra]
            chosen |= set(extra)
        if picked and len(picked) < count:
            # The whole pool is smaller than a set, so cycle through it again.
            base = list(picked)
            random.shuffle(base)
            while len(picked) < count:
                picked.append(base[len(picked) % len(base)])
    return picked


class NoQuestionsError(Exception):
    pass


def create_set(db: Session, user: User, code: str) -> PracticeSet:
    settings = get_settings()
    picks = pick_question_ids(db, user.id, code, settings.questions_per_set)
    if not picks:
        raise NoQuestionsError(code)
    questions = {q.id: q for q in db.scalars(select(Question).where(Question.id.in_({qid for qid, _ in picks})))}
    practice_set = PracticeSet(
        user_id=user.id, mode="drill", task_type_code=code, question_count=len(picks)
    )
    db.add(practice_set)
    for position, (qid, from_backup) in enumerate(picks, start=1):
        question = questions[qid]
        seed = secrets.randbits(62)
        rendered = render(code, question.payload, source_data(question.source), seed)
        practice_set.questions.append(
            SetQuestion(
                question_id=qid,
                position=position,
                task_type_code=code,
                section=TYPES_BY_CODE[code].section,
                variant_seed=seed,
                rendered_payload=rendered,
                drew_from_backup=from_backup,
            )
        )
        question.times_served += 1
    db.flush()
    return practice_set
