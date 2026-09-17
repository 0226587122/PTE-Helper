from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.models import AIFeedback, PracticeSet, Question, QuestionReport, SetQuestion, utc_now
from app.scoring import estimated_score, score_answer
from app.security import DB, CurrentUser
from app.services import pool
from app.services.draw import NoQuestionsError, create_set
from app.services.feedback import FeedbackError, get_or_create_feedback
from app.task_types import TYPES_BY_CODE

router = APIRouter(prefix="/api", tags=["practice"])


class CreateSetIn(BaseModel):
    task_type: str


class SetQuestionSummary(BaseModel):
    position: int
    set_question_id: int
    answered: bool
    score_pct: float | None


class SetOut(BaseModel):
    id: int
    task_type: str
    question_count: int
    started_at: datetime
    finished_at: datetime | None
    average_pct: float | None
    estimated_score: int | None
    answered_count: int
    questions: list[SetQuestionSummary]


class FeedbackOut(BaseModel):
    model: str
    score: int
    traits: list[dict[str, Any]]
    strengths: list[str]
    improvements: list[str]
    model_answer: str
    created_at: datetime


class QuestionOut(BaseModel):
    set_id: int
    position: int
    set_question_id: int
    question_id: int
    task_type: str
    display: dict[str, Any]
    answered: bool
    # Only filled in once the question has been answered.
    response: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    answer: dict[str, Any] | None = None
    feedback: FeedbackOut | None = None


class AnswerIn(BaseModel):
    response: dict[str, Any]


class ReportIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def _set_out(practice_set: PracticeSet) -> SetOut:
    questions = [
        SetQuestionSummary(
            position=q.position, set_question_id=q.id, answered=q.response is not None, score_pct=q.score_pct
        )
        for q in practice_set.questions
    ]
    return SetOut(
        id=practice_set.id,
        task_type=practice_set.task_type_code,
        question_count=practice_set.question_count,
        started_at=practice_set.started_at,
        finished_at=practice_set.finished_at,
        average_pct=practice_set.average_pct,
        estimated_score=practice_set.estimated_score,
        answered_count=sum(1 for q in questions if q.answered),
        questions=questions,
    )


def _feedback_out(feedback: AIFeedback | None) -> FeedbackOut | None:
    if feedback is None:
        return None
    return FeedbackOut(
        model=feedback.model, score=feedback.score, traits=feedback.traits, strengths=feedback.strengths,
        improvements=feedback.improvements, model_answer=feedback.model_answer, created_at=feedback.created_at,
    )


def _question_out(db: DB, sq: SetQuestion) -> QuestionOut:
    out = QuestionOut(
        set_id=sq.set_id,
        position=sq.position,
        set_question_id=sq.id,
        question_id=sq.question_id,
        task_type=sq.practice_set.task_type_code,
        display=sq.rendered_payload["display"],
        answered=sq.response is not None,
    )
    if sq.response is not None:
        out.response = sq.response
        out.result = sq.score_detail
        out.answer = sq.rendered_payload["answer"]
        out.feedback = _feedback_out(db.scalars(select(AIFeedback).where(AIFeedback.set_question_id == sq.id)).first())
    return out


def _own_set(db: DB, user_id: int, set_id: int) -> PracticeSet:
    practice_set = db.get(PracticeSet, set_id)
    if practice_set is None or practice_set.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We couldn't find that practice set.")
    return practice_set


def _set_question(practice_set: PracticeSet, position: int) -> SetQuestion:
    for sq in practice_set.questions:
        if sq.position == position:
            return sq
    raise HTTPException(status.HTTP_404_NOT_FOUND, "That question isn't part of this set.")


@router.post("/sets", response_model=SetOut, status_code=status.HTTP_201_CREATED)
def start_set(body: CreateSetIn, user: CurrentUser, db: DB) -> SetOut:
    code = body.task_type.upper()
    if code not in TYPES_BY_CODE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That task type doesn't exist.")
    try:
        practice_set = create_set(db, user, code)
    except NoQuestionsError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "There are no questions for this task yet.") from None
    db.commit()
    db.refresh(practice_set)
    return _set_out(practice_set)


@router.get("/sets/{set_id}", response_model=SetOut)
def get_set(set_id: int, user: CurrentUser, db: DB) -> SetOut:
    return _set_out(_own_set(db, user.id, set_id))


@router.get("/sets/{set_id}/questions/{position}", response_model=QuestionOut)
def get_question(set_id: int, position: int, user: CurrentUser, db: DB) -> QuestionOut:
    practice_set = _own_set(db, user.id, set_id)
    return _question_out(db, _set_question(practice_set, position))


@router.post("/sets/{set_id}/questions/{position}/answer", response_model=QuestionOut)
def answer_question(set_id: int, position: int, body: AnswerIn, user: CurrentUser, db: DB) -> QuestionOut:
    practice_set = _own_set(db, user.id, set_id)
    if practice_set.finished_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This set is already finished.")
    sq = _set_question(practice_set, position)
    if sq.response is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You've already answered this question.")
    result = score_answer(practice_set.task_type_code, sq.rendered_payload, body.response)
    sq.response = body.response
    sq.score_pct = result.pct
    sq.score_detail = result.to_dict()
    sq.answered_at = utc_now()
    db.commit()
    return _question_out(db, sq)


@router.post("/sets/{set_id}/finish", response_model=SetOut)
def finish_set(set_id: int, user: CurrentUser, db: DB) -> SetOut:
    practice_set = _own_set(db, user.id, set_id)
    if practice_set.finished_at is None:
        # Unanswered questions count as zero, so finishing early doesn't inflate the estimate.
        scores = [q.score_pct or 0.0 for q in practice_set.questions]
        average = round(sum(scores) / len(scores), 1) if scores else 0.0
        practice_set.average_pct = average
        practice_set.estimated_score = estimated_score(average)
        practice_set.finished_at = utc_now()
        db.commit()
    return _set_out(practice_set)


@router.get("/sets/{set_id}/review", response_model=list[QuestionOut])
def review_set(set_id: int, user: CurrentUser, db: DB) -> list[QuestionOut]:
    practice_set = _own_set(db, user.id, set_id)
    return [_question_out(db, sq) for sq in practice_set.questions]


def _own_set_question(db: DB, user_id: int, set_question_id: int) -> SetQuestion:
    sq = db.get(SetQuestion, set_question_id)
    if sq is None or sq.practice_set.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We couldn't find that question.")
    return sq


@router.post("/set-questions/{set_question_id}/feedback", response_model=FeedbackOut)
def request_feedback(set_question_id: int, user: CurrentUser, db: DB) -> FeedbackOut:
    sq = _own_set_question(db, user.id, set_question_id)
    try:
        feedback = get_or_create_feedback(db, user, sq)
    except FeedbackError as exc:
        raise HTTPException(exc.status_code, exc.message) from None
    out = _feedback_out(feedback)
    assert out
    return out


@router.post("/questions/{question_id}/report", status_code=status.HTTP_201_CREATED)
def report(question_id: int, body: ReportIn, user: CurrentUser, db: DB) -> dict[str, str]:
    question = db.get(Question, question_id)
    seen = db.scalars(
        select(SetQuestion.id)
        .join(PracticeSet, PracticeSet.id == SetQuestion.set_id)
        .where(SetQuestion.question_id == question_id, PracticeSet.user_id == user.id)
        .limit(1)
    ).first()
    if question is None or seen is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We couldn't find that question.")
    already = db.scalars(
        select(QuestionReport.id).where(
            QuestionReport.question_id == question_id,
            QuestionReport.user_id == user.id,
            QuestionReport.resolved_at.is_(None),
        )
    ).first()
    if already:
        return {"message": "Thanks, you've already reported this question. We'll take a look."}
    pool.report_question(db, question, user, body.reason.strip())
    db.commit()
    return {"message": "Thanks for letting us know. We'll review this question."}
