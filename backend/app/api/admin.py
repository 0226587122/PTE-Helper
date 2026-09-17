from collections import defaultdict
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.bank.validation import content_hash, validate_payload, validate_source
from app.models import ContentSource, Question, QuestionReport, utc_now
from app.security import DB, AdminUser
from app.services import pool
from app.task_types import TYPES, TYPES_BY_CODE

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _source_dict(source: ContentSource | None) -> dict[str, Any] | None:
    if source is None:
        return None
    return {
        "id": source.id,
        "source_key": source.source_key,
        "kind": source.kind,
        "title": source.title,
        "body": source.body,
        "blank_markup": source.blank_markup,
        "turns": source.turns,
    }


def _preview(question: Question) -> str:
    p = question.payload
    for key in ("text", "sentence", "question", "prompt", "situation", "title"):
        if isinstance(p.get(key), str):
            return p[key][:140]
    if question.source is not None:
        return question.source.title
    if isinstance(p.get("paragraphs"), list) and p["paragraphs"]:
        return p["paragraphs"][0][:140]
    return ""


class TypeSummary(BaseModel):
    code: str
    name: str
    active: int
    backup: int
    retired: int
    open_reports: int


@router.get("/summary", response_model=list[TypeSummary])
def summary(_: AdminUser, db: DB) -> list[TypeSummary]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for code, status_, n in db.execute(
        select(Question.task_type_code, Question.status, func.count()).group_by(Question.task_type_code, Question.status)
    ):
        counts[code][status_] = n
    reports: dict[str, int] = defaultdict(int)
    for code, n in db.execute(
        select(Question.task_type_code, func.count())
        .join(QuestionReport, QuestionReport.question_id == Question.id)
        .where(QuestionReport.resolved_at.is_(None))
        .group_by(Question.task_type_code)
    ):
        reports[code] = n
    return [
        TypeSummary(
            code=t.code, name=t.name, active=counts[t.code]["active"], backup=counts[t.code]["backup"],
            retired=counts[t.code]["retired"], open_reports=reports[t.code],
        )
        for t in TYPES
    ]


class QuestionRow(BaseModel):
    id: int
    task_type: str
    status: str
    source_key: str | None
    preview: str
    difficulty: int | None
    report_count: int
    open_reports: int
    times_served: int
    created_at: datetime


class QuestionPage(BaseModel):
    items: list[QuestionRow]
    total: int
    page: int
    page_size: int


def _open_reports_by_question(db: DB, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    rows = db.execute(
        select(QuestionReport.question_id, func.count())
        .where(QuestionReport.question_id.in_(ids), QuestionReport.resolved_at.is_(None))
        .group_by(QuestionReport.question_id)
    )
    return dict(rows.all())


@router.get("/questions", response_model=QuestionPage)
def list_questions(
    _: AdminUser,
    db: DB,
    task_type: str | None = None,
    status_filter: Literal["active", "backup", "retired"] | None = Query(None, alias="status"),
    reported: bool = False,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> QuestionPage:
    query = select(Question).outerjoin(ContentSource, ContentSource.id == Question.source_id)
    if task_type:
        query = query.where(Question.task_type_code == task_type.upper())
    if status_filter:
        query = query.where(Question.status == status_filter)
    if reported:
        open_ids = select(QuestionReport.question_id).where(QuestionReport.resolved_at.is_(None))
        query = query.where(Question.id.in_(open_ids))
    if search:
        like = f"%{search}%"
        query = query.where(
            or_(
                func.json_unquote(Question.payload).like(like),
                ContentSource.title.like(like),
                ContentSource.source_key.like(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Question.task_type_code, Question.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    open_reports = _open_reports_by_question(db, [q.id for q in rows])
    items = [
        QuestionRow(
            id=q.id, task_type=q.task_type_code, status=q.status,
            source_key=q.source.source_key if q.source else None, preview=_preview(q), difficulty=q.difficulty,
            report_count=q.report_count, open_reports=open_reports.get(q.id, 0), times_served=q.times_served,
            created_at=q.created_at,
        )
        for q in rows
    ]
    return QuestionPage(items=items, total=total, page=page, page_size=page_size)


class ReportOut(BaseModel):
    id: int
    question_id: int
    user_id: int
    reason: str
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class QuestionDetail(BaseModel):
    id: int
    task_type: str
    status: str
    difficulty: int | None
    payload: dict[str, Any]
    source: dict[str, Any] | None
    report_count: int
    times_served: int
    created_at: datetime
    promoted_at: datetime | None
    retired_at: datetime | None
    reports: list[ReportOut]
    promoted_ids: list[int] = []


def _detail(db: DB, question: Question, promoted: list[Question] | None = None) -> QuestionDetail:
    reports = db.scalars(
        select(QuestionReport).where(QuestionReport.question_id == question.id).order_by(QuestionReport.created_at.desc())
    ).all()
    return QuestionDetail(
        id=question.id, task_type=question.task_type_code, status=question.status, difficulty=question.difficulty,
        payload=question.payload, source=_source_dict(question.source), report_count=question.report_count,
        times_served=question.times_served, created_at=question.created_at, promoted_at=question.promoted_at,
        retired_at=question.retired_at, reports=[ReportOut.model_validate(r) for r in reports],
        promoted_ids=[q.id for q in promoted or []],
    )


def _get_question(db: DB, question_id: int) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    return question


@router.get("/questions/{question_id}", response_model=QuestionDetail)
def get_question(question_id: int, _: AdminUser, db: DB) -> QuestionDetail:
    return _detail(db, _get_question(db, question_id))


class QuestionPatch(BaseModel):
    payload: dict[str, Any] | None = None
    status: Literal["active", "backup", "retired"] | None = None
    difficulty: int | None = Field(None, ge=1, le=3)


@router.patch("/questions/{question_id}", response_model=QuestionDetail)
def update_question(question_id: int, body: QuestionPatch, _: AdminUser, db: DB) -> QuestionDetail:
    question = _get_question(db, question_id)
    if body.payload is not None:
        errors = validate_payload(question.task_type_code, body.payload, _source_dict(question.source))
        if errors:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"message": "The payload isn't valid.", "errors": errors})
        digest = content_hash(
            question.task_type_code, question.source.source_key if question.source else None, body.payload
        )
        clash = db.scalars(
            select(Question.id).where(
                Question.task_type_code == question.task_type_code, Question.content_hash == digest, Question.id != question.id
            )
        ).first()
        if clash:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Question {clash} already has exactly this content.")
        question.payload = body.payload
        question.content_hash = digest
    if body.difficulty is not None:
        question.difficulty = body.difficulty
    promoted: list[Question] = []
    if body.status is not None and body.status != question.status:
        promoted = pool.set_status(db, question, body.status)
    db.commit()
    return _detail(db, question, promoted)


class PromoteIn(BaseModel):
    question_id: int | None = None


@router.post("/task-types/{code}/promote", response_model=QuestionDetail)
def promote(code: str, body: PromoteIn, _: AdminUser, db: DB) -> QuestionDetail:
    code = code.upper()
    if code not in TYPES_BY_CODE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown task type.")
    question = pool.promote_backup(db, code, body.question_id)
    if question is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "There's no matching backup question to promote.")
    db.commit()
    return _detail(db, question)


class SourcePatch(BaseModel):
    title: str | None = None
    body: str | None = None
    blank_markup: str | None = None
    turns: list[dict[str, Any]] | None = None


@router.patch("/sources/{source_id}")
def update_source(source_id: int, body: SourcePatch, _: AdminUser, db: DB) -> dict[str, Any]:
    source = db.get(ContentSource, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")
    updated = _source_dict(source) or {}
    updated.update(body.model_dump(exclude_unset=True))
    errors = validate_source(updated)
    for question in db.scalars(select(Question).where(Question.source_id == source.id)):
        errors += [f"question {question.id} ({question.task_type_code}): {e}" for e in validate_payload(question.task_type_code, question.payload, updated)]
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"message": "The source isn't valid.", "errors": errors})
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    db.commit()
    return _source_dict(source) or {}


@router.get("/reports", response_model=list[ReportOut])
def list_reports(_: AdminUser, db: DB, open_only: bool = Query(True, alias="open")) -> list[QuestionReport]:
    query = select(QuestionReport).order_by(QuestionReport.created_at.desc()).limit(200)
    if open_only:
        query = query.where(QuestionReport.resolved_at.is_(None))
    return list(db.scalars(query))


@router.post("/reports/{report_id}/resolve", response_model=ReportOut)
def resolve_report(report_id: int, _: AdminUser, db: DB) -> QuestionReport:
    report = db.get(QuestionReport, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found.")
    if report.resolved_at is None:
        report.resolved_at = utc_now()
        db.commit()
    return report
