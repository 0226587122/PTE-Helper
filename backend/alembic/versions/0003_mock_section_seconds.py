"""Store each mock test's pooled part length

The reading part's clock now follows the number of questions drawn for that attempt, so the length
is stored with the attempt instead of being a fixed constant.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("practice_sets", sa.Column("section_seconds", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("practice_sets", "section_seconds")
