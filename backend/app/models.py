"""SQLAlchemy ORM models. Every table has a primary key (DigitalOcean enforces sql_require_primary_key)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

USER_ROLES = ("student", "admin")
SECTIONS = ("speaking_writing", "reading", "listening")
SOURCE_KINDS = ("lecture", "passage", "discussion")
QUESTION_STATUSES = ("active", "backup", "retired")
SET_MODES = ("drill", "mock")


def utc_now() -> datetime:
    """Current UTC time without tzinfo, matching MySQL DATETIME columns."""
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(Enum(*USER_ROLES, name="user_role"), default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TaskType(Base):
    __tablename__ = "task_types"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    section: Mapped[str] = mapped_column(Enum(*SECTIONS, name="section"))
    prep_seconds: Mapped[int] = mapped_column(Integer, default=0)
    answer_seconds: Mapped[int] = mapped_column(Integer)
    ai_feedback: Mapped[bool] = mapped_column(Boolean, default=False)
    tip: Mapped[str] = mapped_column(Text)
    instructions: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer)


class ContentSource(Base):
    __tablename__ = "content_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[str] = mapped_column(Enum(*SOURCE_KINDS, name="source_kind"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    blank_markup: Mapped[str | None] = mapped_column(Text, nullable=True)
    turns: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_type_status", "task_type_code", "status"),
        UniqueConstraint("task_type_code", "content_hash", name="uq_questions_type_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_type_code: Mapped[str] = mapped_column(ForeignKey("task_types.code"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("content_sources.id"), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(Enum(*QUESTION_STATUSES, name="question_status"), default="active")
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_count: Mapped[int] = mapped_column(Integer, default=0)
    times_served: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    source: Mapped[ContentSource | None] = relationship()
    task_type: Mapped[TaskType] = relationship()


class PracticeSet(Base):
    __tablename__ = "practice_sets"
    __table_args__ = (Index("ix_practice_sets_user_type", "user_id", "task_type_code", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(Enum(*SET_MODES, name="set_mode"), default="drill")
    # Null for a full mock test, which covers every task type.
    task_type_code: Mapped[str | None] = mapped_column(ForeignKey("task_types.code"), nullable=True)
    question_count: Mapped[int] = mapped_column(Integer)
    blueprint_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # When each part's clock runs out, as {"reading": "2026-09-18T01:02:03"}. Set when a part starts.
    section_deadlines: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    # The furthest item the student has reached, so a refresh resumes in the right place.
    current_position: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    average_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    questions: Mapped[list["SetQuestion"]] = relationship(
        back_populates="practice_set", order_by="SetQuestion.position", cascade="all, delete-orphan"
    )


class SetQuestion(Base):
    __tablename__ = "set_questions"
    __table_args__ = (UniqueConstraint("set_id", "position", name="uq_set_questions_set_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("practice_sets.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    position: Mapped[int] = mapped_column(Integer)
    task_type_code: Mapped[str | None] = mapped_column(ForeignKey("task_types.code"), nullable=True)
    section: Mapped[str | None] = mapped_column(Enum(*SECTIONS, name="section"), nullable=True)
    variant_seed: Mapped[int] = mapped_column(BigInteger)
    rendered_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    score_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    drew_from_backup: Mapped[bool] = mapped_column(Boolean, default=False)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    served_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # True when the answer arrived after the deadline, which scores zero like an unanswered item.
    late: Mapped[bool] = mapped_column(Boolean, default=False)

    practice_set: Mapped[PracticeSet] = relationship(back_populates="questions")
    question: Mapped[Question] = relationship()


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_question_id: Mapped[int] = mapped_column(
        ForeignKey("set_questions.id", ondelete="CASCADE"), unique=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    model: Mapped[str] = mapped_column(String(100))
    score: Mapped[int] = mapped_column(Integer)
    traits: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    strengths: Mapped[list[str]] = mapped_column(JSON)
    improvements: Mapped[list[str]] = mapped_column(JSON)
    model_answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class QuestionReport(Base):
    __tablename__ = "question_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
