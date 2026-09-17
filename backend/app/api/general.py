from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, text

from app.models import PracticeSet, TaskType
from app.security import DB, CurrentUser
from app.task_types import TYPES_BY_CODE

router = APIRouter(prefix="/api", tags=["general"])


@router.get("/health")
def health(db: DB) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - any database failure means unhealthy
        return JSONResponse({"status": "error", "database": "unreachable"}, status_code=503)
    return JSONResponse({"status": "ok", "database": "ok"})


class TaskTypeOut(BaseModel):
    code: str
    name: str
    section: str
    prep_seconds: int
    answer_seconds: int
    ai_feedback: bool
    tip: str
    instructions: str
    sort_order: int
    audio: bool
    replay: bool
    spoken: bool


@router.get("/task-types", response_model=list[TaskTypeOut])
def task_types(db: DB) -> list[TaskTypeOut]:
    rows = db.scalars(select(TaskType).order_by(TaskType.sort_order)).all()
    if not rows:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Task types haven't been loaded yet. Run the seed script.")
    out = []
    for row in rows:
        definition = TYPES_BY_CODE.get(row.code)
        if definition is None:
            continue
        out.append(
            TaskTypeOut(
                code=row.code, name=row.name, section=row.section, prep_seconds=row.prep_seconds,
                answer_seconds=row.answer_seconds, ai_feedback=row.ai_feedback, tip=row.tip,
                instructions=row.instructions, sort_order=row.sort_order,
                audio=definition.audio, replay=definition.replay, spoken=definition.spoken,
            )
        )
    return out


class TypeProgress(BaseModel):
    code: str
    sets_completed: int
    best_score: int | None
    last_score: int | None
    last_practised: datetime | None


class HistoryItem(BaseModel):
    set_id: int
    code: str
    name: str
    finished_at: datetime
    average_pct: float
    estimated_score: int


class ProgressOut(BaseModel):
    types: list[TypeProgress]
    recent: list[HistoryItem]
    overall_estimate: int | None


@router.get("/me/progress", response_model=ProgressOut)
def progress(user: CurrentUser, db: DB) -> ProgressOut:
    finished = db.scalars(
        select(PracticeSet)
        .where(PracticeSet.user_id == user.id, PracticeSet.finished_at.is_not(None))
        .order_by(PracticeSet.finished_at.desc(), PracticeSet.id.desc())
    ).all()
    by_type: dict[str, list[PracticeSet]] = {}
    for s in finished:
        by_type.setdefault(s.task_type_code, []).append(s)
    types = [
        TypeProgress(
            code=code,
            sets_completed=len(sets),
            best_score=max(s.estimated_score or 0 for s in sets),
            last_score=sets[0].estimated_score,
            last_practised=sets[0].finished_at,
        )
        for code, sets in by_type.items()
    ]
    recent = [
        HistoryItem(
            set_id=s.id, code=s.task_type_code, name=TYPES_BY_CODE[s.task_type_code].name,
            finished_at=s.finished_at, average_pct=s.average_pct or 0, estimated_score=s.estimated_score or 10,
        )
        for s in finished[:20]
    ]
    last_scores = [t.last_score for t in types if t.last_score is not None]
    overall = round(sum(last_scores) / len(last_scores)) if last_scores else None
    return ProgressOut(types=types, recent=recent, overall_estimate=overall)
