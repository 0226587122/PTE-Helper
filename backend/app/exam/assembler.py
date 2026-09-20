"""Builds one full mock test for a student from the blueprint."""

import logging
import random
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exam.blueprint import BLUEPRINT_VERSION
from app.exam.mix import MockMix, build_mix
from app.models import PracticeSet, Question, SetQuestion, User
from app.services.draw import pick_question_ids, source_data
from app.variants import render

log = logging.getLogger(__name__)


class NotEnoughQuestionsError(Exception):
    pass


def assemble(db: Session, user: User, rng: random.Random | None = None, mix: MockMix | None = None) -> PracticeSet:
    """Create a mock test: the drawn mix of task types, in exam order, with no source text repeated."""
    rng = rng or random.Random()
    mix = mix or build_mix(rng)

    # No lecture, passage or discussion appears twice in one test, so nothing is given away by a
    # question the student has already seen earlier in the same sitting.
    used_sources: set[int] = set()
    picks: list[tuple[str, str, int, bool]] = []  # (code, section, question_id, from_backup)

    for code, section in mix.ordered_items():
        chosen = pick_question_ids(db, user.id, code, 1, exclude_sources=used_sources)
        if not chosen:
            # Everything of this type shares a source already used, so allow a repeat rather than
            # dropping a task type out of the test.
            chosen = pick_question_ids(db, user.id, code, 1)
        if not chosen:
            raise NotEnoughQuestionsError(code)
        question_id, from_backup = chosen[0]
        picks.append((code, section, question_id, from_backup))

        source_id = db.scalar(select(Question.source_id).where(Question.id == question_id))
        if source_id:
            used_sources.add(source_id)

    questions = {q.id: q for q in db.scalars(select(Question).where(Question.id.in_({p[2] for p in picks})))}
    practice_set = PracticeSet(
        user_id=user.id,
        mode="mock",
        task_type_code=None,
        question_count=len(picks),
        blueprint_version=BLUEPRINT_VERSION,
        current_position=1,
        section_deadlines={},
        # Parts that run on one clock get their length from the mix, so a shorter reading part
        # gets proportionally less time, as in the real test.
        section_seconds=mix.pooled_seconds(),
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
