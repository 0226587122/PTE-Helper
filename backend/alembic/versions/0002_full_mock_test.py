"""Full mock test support

Adds the fields a full mock test needs: the attempt mode, the blueprint version, the clock for each
part, and per-item type, part and deadline.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SECTION = sa.Enum("speaking_writing", "reading", "listening", name="section")


def upgrade() -> None:
    op.add_column(
        "practice_sets",
        sa.Column("mode", sa.Enum("drill", "mock", name="set_mode"), nullable=False, server_default="drill"),
    )
    op.add_column("practice_sets", sa.Column("blueprint_version", sa.String(40), nullable=True))
    op.add_column("practice_sets", sa.Column("section_deadlines", sa.JSON(), nullable=True))
    op.add_column(
        "practice_sets", sa.Column("current_position", sa.Integer(), nullable=False, server_default="1")
    )
    # A full mock test covers every task type, so the set-level type becomes optional.
    op.alter_column("practice_sets", "task_type_code", existing_type=sa.String(10), nullable=True)

    op.add_column("set_questions", sa.Column("task_type_code", sa.String(10), nullable=True))
    op.add_column("set_questions", sa.Column("section", SECTION, nullable=True))
    op.add_column("set_questions", sa.Column("served_at", sa.DateTime(), nullable=True))
    op.add_column("set_questions", sa.Column("deadline_at", sa.DateTime(), nullable=True))
    op.add_column(
        "set_questions", sa.Column("late", sa.Boolean(), nullable=False, server_default=sa.text("0"))
    )
    op.create_foreign_key(
        "fk_set_questions_task_type", "set_questions", "task_types", ["task_type_code"], ["code"]
    )

    # Existing drill items belong to their set's single task type.
    op.execute(
        """
        UPDATE set_questions sq
        JOIN practice_sets ps ON ps.id = sq.set_id
        JOIN task_types tt ON tt.code = ps.task_type_code
        SET sq.task_type_code = ps.task_type_code, sq.section = tt.section
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_set_questions_task_type", "set_questions", type_="foreignkey")
    for column in ("late", "deadline_at", "served_at", "section", "task_type_code"):
        op.drop_column("set_questions", column)
    op.alter_column("practice_sets", "task_type_code", existing_type=sa.String(10), nullable=False)
    for column in ("current_position", "section_deadlines", "blueprint_version", "mode"):
        op.drop_column("practice_sets", column)
