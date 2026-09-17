"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

MYSQL = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role", sa.Enum("student", "admin", name="user_role"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        **MYSQL,
    )
    op.create_table(
        "task_types",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("section", sa.Enum("speaking_writing", "reading", "listening", name="section"), nullable=False),
        sa.Column("prep_seconds", sa.Integer(), nullable=False),
        sa.Column("answer_seconds", sa.Integer(), nullable=False),
        sa.Column("ai_feedback", sa.Boolean(), nullable=False),
        sa.Column("tip", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        **MYSQL,
    )
    op.create_table(
        "content_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_key", sa.String(100), nullable=False, unique=True),
        sa.Column("kind", sa.Enum("lecture", "passage", "discussion", name="source_kind"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("blank_markup", sa.Text(), nullable=True),
        sa.Column("turns", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        **MYSQL,
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_type_code", sa.String(10), sa.ForeignKey("task_types.code"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("content_sources.id"), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.Enum("active", "backup", "retired", name="question_status"), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=True),
        sa.Column("report_count", sa.Integer(), nullable=False),
        sa.Column("times_served", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("promoted_at", sa.DateTime(), nullable=True),
        sa.Column("retired_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("task_type_code", "content_hash", name="uq_questions_type_hash"),
        **MYSQL,
    )
    op.create_index("ix_questions_type_status", "questions", ["task_type_code", "status"])
    op.create_table(
        "practice_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type_code", sa.String(10), sa.ForeignKey("task_types.code"), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("average_pct", sa.Float(), nullable=True),
        sa.Column("estimated_score", sa.Integer(), nullable=True),
        **MYSQL,
    )
    op.create_index("ix_practice_sets_user_type", "practice_sets", ["user_id", "task_type_code", "started_at"])
    op.create_table(
        "set_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("set_id", sa.Integer(), sa.ForeignKey("practice_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("variant_seed", sa.BigInteger(), nullable=False),
        sa.Column("rendered_payload", sa.JSON(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("score_pct", sa.Float(), nullable=True),
        sa.Column("score_detail", sa.JSON(), nullable=True),
        sa.Column("drew_from_backup", sa.Boolean(), nullable=False),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("set_id", "position", name="uq_set_questions_set_position"),
        **MYSQL,
    )
    op.create_table(
        "ai_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "set_question_id", sa.Integer(), sa.ForeignKey("set_questions.id", ondelete="CASCADE"), nullable=False,
            unique=True,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("traits", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("improvements", sa.JSON(), nullable=False),
        sa.Column("model_answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        **MYSQL,
    )
    op.create_index("ix_ai_feedback_user_id", "ai_feedback", ["user_id"])
    op.create_index("ix_ai_feedback_created_at", "ai_feedback", ["created_at"])
    op.create_table(
        "question_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        **MYSQL,
    )
    op.create_index("ix_question_reports_question_id", "question_reports", ["question_id"])


def downgrade() -> None:
    for table in (
        "question_reports", "ai_feedback", "set_questions", "practice_sets", "questions", "content_sources",
        "task_types", "users",
    ):
        op.drop_table(table)
