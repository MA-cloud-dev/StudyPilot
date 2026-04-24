"""add soft delete fields to plans"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_0004"
down_revision = "20260408_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("macro_plans", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("micro_plans", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("micro_plans", "deleted_at")
    op.drop_column("macro_plans", "deleted_at")
