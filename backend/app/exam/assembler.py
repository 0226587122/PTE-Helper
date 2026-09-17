"""Builds one full mock test for a student from the blueprint."""

import logging
import random
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exam.blueprint import BLUEPRINT_VERSION, PARTS
from app.models import PracticeSet, Question, SetQuestion, User
from app.services.draw import pick_question_ids, source_data
from app.variants import render

log = logging.getLogger(__name__)


class NotEnoughQuestionsError(Exception):
    pass


def assemble(db: Session, user: User, rng: random.Random | None = None) -> PracticeSet:
    """Create a mock test: every task type in exam order, with counts drawn from the blueprint ranges."""
    rng = rng or random.Random()
    picks: list[tuple[str, str, int, bool]] = []  # (code, section, question_id, from_backup)

    for part in PARTS:
        for spec in part.items:
            count = rng.randint(*spec.count)
            chosen = pick_question_ids(db, user.id, spec.code, count)
            if not chosen:
                raise NotEnoughQuestionsError(spec.code)
            if len(chosen) < count:
                log.warning("Mock test for user %s has only %s of %s %s items", user.id, len(chosen), count, spec.code)
            picks += [(spec.code, part.section, qid, backup) for qid, backup in chosen]

    questions = {q.id: q for q in db.scalars(select(Question).where(Question.id.in_({p[2] for p in picks})))}
    practice_set = PracticeSet(
        user_id=user.id,
        mode="mock",
        task_type_code=None,
        question_count=len(picks),
        blueprint_version=BLUEPRINT_VERSION,
        current_position=1,
        section_deadlines={},
    )
    db.add(practice_set)

    for position, (code, section, question_id, from_backup) in enumerate(picks, start=1):
        question = questions[question_id]
        seed = secrets.randbits(62)
        practice_set.questions.append(
            SetQuestion(
                question_id=question_id,
                position=position,
                task_type_code=code,
                section=section,
                variant_seed=seed,
                rendered_payload=render(code, question.payload, source_data(question.source), seed),
                drew_from_backup=from_backup,
            )
        )
        question.times_served += 1
    db.flush()
    return practice_set
