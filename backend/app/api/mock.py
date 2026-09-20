"""Full mock test: all three parts back to back, real timing, no feedback until the end."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.exam import clock
from app.exam.assembler import NotEnoughQuestionsError, assemble
from app.exam.blueprint import BLUEPRINT_VERSION, PARTS, PARTS_BY_SECTION, PERSONAL_INTRODUCTION, item_count_range, part_minutes, total_minutes
from app.models import PracticeSet, SetQuestion, utc_now
from app.scoring import estimated_score, score_answer
from app.scoring.aggregate import build_report, item_percent
from app.security import DB, CurrentUser
from app.task_types import TYPES_BY_CODE

router = APIRouter(prefix="/api/mock-tests", tags=["mock test"])


class ItemState(BaseModel):
    position: int
    task_type: str
    task_name: str
    section: str
    answered: bool
    late: bool


class MockState(BaseModel):
    id: int
    blueprint_version: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    question_count: int
    current_position: int
    answered_count: int
    server_time: datetime
    section_deadlines: dict[str, datetime]
    items: list[ItemState]


class MockQuestion(BaseModel):
    set_id: int
    position: int
    set_question_id: int
    question_id: int
    task_type: str
    section: str
    part_title: str
    display: dict[str, Any]
    answered: bool
    response: dict[str, Any] | None
    # Timing for this item, from the blueprint.
    prep_seconds: int
    answer_seconds: int
    deadline_at: datetime
    seconds_remaining: int
    section_deadline_at: datetime | None
    section_seconds_remaining: int | None
    allow_back: bool
    # True when this item starts a new part, so the runner can show the part introduction.
    starts_part: bool
    server_time: datetime


class AnswerIn(BaseModel):
    response: dict[str, Any]


class AnswerAck(BaseModel):
    """A mock test never reveals the score, so this only confirms the answer was stored."""

    position: int
    accepted: bool
    late: bool
    next_position: int | None
    finished: bool


def _blueprint_summary() -> dict[str, Any]:
    low, high = total_minutes()
    items_low, items_high = item_count_range()
    return {
        "blueprint_version": BLUEPRINT_VERSION,
        "minutes": {"min": low, "max": high},
        "items": {"min": items_low, "max": items_high},
        "personal_introduction": PERSONAL_INTRODUCTION,
        "parts": [
            {
                "section": part.section,
                "title": part.title,
                "instructions": part.instructions,
                "allow_back": part.allow_back,
                "minutes": dict(zip(("min", "max"), part_minutes(part))),
                "task_types": [
                    {"code": spec.code, "name": spec.name, "count": list(spec.count), "skills": list(spec.skills)}
                    for spec in part.items
                ],
            }
            for part in PARTS
        ],
    }


@router.get("/blueprint")
def blueprint(_: CurrentUser) -> dict[str, Any]:
    """What a mock test contains: parts, task types, item counts and timing."""
    return _blueprint_summary()


def _state(practice_set: PracticeSet, db: DB) -> MockState:
    items = practice_set.questions
    deadlines = {
        section: datetime.fromisoformat(value)
        for section, value in (practice_set.section_deadlines or {}).items()
        if value
    }
    return MockState(
        id=practice_set.id,
        blueprint_version=practice_set.blueprint_version or BLUEPRINT_VERSION,
        status="finished" if practice_set.finished_at else "in_progress",
        started_at=practice_set.started_at,
        finished_at=practice_set.finished_at,
        question_count=practice_set.question_count,
        current_position=practice_set.current_position,
        answered_count=sum(1 for item in items if item.response is not None),
        server_time=utc_now(),
        section_deadlines=deadlines,
        items=[
            ItemState(
                position=item.position,
                task_type=item.task_type_code or "",
                task_name=TYPES_BY_CODE[item.task_type_code or ""].name,
                section=item.section or "",
                answered=item.response is not None,
                late=item.late,
            )
            for item in items
        ],
    )


def _own_mock(db: DB, user_id: int, set_id: int) -> PracticeSet:
    practice_set = db.get(PracticeSet, set_id)
    if practice_set is None or practice_set.user_id != user_id or practice_set.mode != "mock":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We couldn't find that mock test.")
    return practice_set


def _item(practice_set: PracticeSet, position: int) -> SetQuestion:
    for item in practice_set.questions:
        if item.position == position:
            return item
    raise HTTPException(status.HTTP_404_NOT_FOUND, "That question isn't part of this mock test.")


def _score_item(item: SetQuestion, response: dict[str, Any] | None, late: bool) -> None:
    """Score an item now, but never send the score back during the test."""
    if response is None or late:
        item.score_pct = 0.0
        item.score_detail = {"skipped": True, "late": late}
        return
    result = score_answer(item.task_type_code or "", item.rendered_payload, response)
    item.score_pct = result.pct
    item.score_detail = result.to_dict()


def _finish(practice_set: PracticeSet, db: DB) -> None:
    if practice_set.finished_at is not None:
        return
    items = practice_set.questions
    for item in items:
        if item.score_pct is None:
            _score_item(item, item.response, item.late)
    scores = [item_percent(item) for item in items]
    practice_set.average_pct = round(sum(scores) / len(scores), 1) if scores else 0.0
    practice_set.estimated_score = estimated_score(practice_set.average_pct)
    practice_set.finished_at = utc_now()
    db.commit()


def _expired(practice_set: PracticeSet) -> bool:
    """True when every part the student has reached has run out of time and nothing is left to answer."""
    now = utc_now()
    unanswered = [item for item in practice_set.questions if item.response is None]
    if not unanswered:
        return True
    for item in unanswered:
        if item.deadline_at is None:
            return False  # not served yet, so the student can still answer it
        if item.deadline_at > now:
            return False
    return True


@router.post("", response_model=MockState, status_code=status.HTTP_201_CREATED)
def start_mock(user: CurrentUser, db: DB) -> MockState:
    """Start a mock test, or return the one already in progress."""
    existing = db.scalars(
        select(PracticeSet)
        .where(PracticeSet.user_id == user.id, PracticeSet.mode == "mock", PracticeSet.finished_at.is_(None))
        .order_by(PracticeSet.started_at.desc())
    ).first()
    if existing:
        return _state(existing, db)
    try:
        practice_set = assemble(db, user)
    except NotEnoughQuestionsError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, f"There aren't enough {exc.args[0]} questions for a mock test yet."
        ) from None
    db.commit()
    db.refresh(practice_set)
    return _state(practice_set, db)


@router.get("/{set_id}", response_model=MockState)
def get_mock(set_id: int, user: CurrentUser, db: DB) -> MockState:
    practice_set = _own_mock(db, user.id, set_id)
    if practice_set.finished_at is None and _expired(practice_set):
        _finish(practice_set, db)
    return _state(practice_set, db)


@router.get("/{set_id}/questions/{position}", response_model=MockQuestion)
def get_question(set_id: int, position: int, user: CurrentUser, db: DB) -> MockQuestion:
    """Serve one item and start its clock. Moving on is one way, except inside the reading part."""
    practice_set = _own_mock(db, user.id, set_id)
    if practice_set.finished_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This mock test is already finished.")
    item = _item(practice_set, position)
    part = PARTS_BY_SECTION[item.section or ""]

    if position > practice_set.current_position:
        if position != practice_set.current_position + 1:
            raise HTTPException(status.HTTP_409_CONFLICT, "Please answer the questions in order.")
        practice_set.current_position = position
    elif position < practice_set.current_position and not part.allow_back:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can't go back to a question you've moved past.")

    deadline = clock.serve(practice_set, item, utc_now())
    previous = _item(practice_set, position - 1) if position > 1 else None
    section_deadline = clock.section_deadline(practice_set, item.section or "")
    definition = TYPES_BY_CODE[item.task_type_code or ""]
    db.commit()

    return MockQuestion(
        set_id=practice_set.id,
        position=item.position,
        set_question_id=item.id,
        question_id=item.question_id,
        task_type=item.task_type_code or "",
        section=item.section or "",
        part_title=part.title,
        display=item.rendered_payload["display"],
        answered=item.response is not None,
        response=item.response,
        prep_seconds=clock.scaled(definition.prep_seconds),
        answer_seconds=clock.scaled(definition.answer_seconds),
        deadline_at=deadline,
        seconds_remaining=clock.remaining_seconds(deadline) or 0,
        section_deadline_at=section_deadline,
        section_seconds_remaining=clock.remaining_seconds(section_deadline),
        allow_back=part.allow_back,
        starts_part=previous is None or previous.section != item.section,
        server_time=utc_now(),
    )


@router.post("/{set_id}/questions/{position}/answer", response_model=AnswerAck)
def answer(set_id: int, position: int, body: AnswerIn, user: CurrentUser, db: DB) -> AnswerAck:
    practice_set = _own_mock(db, user.id, set_id)
    if practice_set.finished_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This mock test is already finished.")
    item = _item(practice_set, position)
    part = PARTS_BY_SECTION[item.section or ""]
    if item.response is not None and not part.allow_back:
        raise HTTPException(status.HTTP_409_CONFLICT, "You've already answered this question.")

    now = utc_now()
    late = clock.is_late(item, now)
    item.response = body.response
    item.answered_at = now
    item.late = late
    _score_item(item, body.response, late)

    next_position = position + 1 if position < practice_set.question_count else None
    if next_position and next_position > practice_set.current_position:
        practice_set.current_position = next_position
    finished = next_position is None or _expired(practice_set)
    if finished:
        _finish(practice_set, db)
    else:
        db.commit()
    return AnswerAck(position=position, accepted=True, late=late, next_position=next_position, finished=finished)


@router.post("/{set_id}/submit")
def submit(set_id: int, user: CurrentUser, db: DB) -> dict[str, Any]:
    """Finish the mock test, scoring anything unanswered as zero, and return the report."""
    practice_set = _own_mock(db, user.id, set_id)
    _finish(practice_set, db)
    return build_report(practice_set, list(practice_set.questions))


@router.get("/{set_id}/report")
def report(set_id: int, user: CurrentUser, db: DB) -> dict[str, Any]:
    practice_set = _own_mock(db, user.id, set_id)
    if practice_set.finished_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This mock test isn't finished yet.")
    return build_report(practice_set, list(practice_set.questions))
