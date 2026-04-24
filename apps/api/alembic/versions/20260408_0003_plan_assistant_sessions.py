"""add plan assistant sessions"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260408_0003"
down_revision = "20260331_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_assistant_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("conversation_turns", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("conversation_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("plan_assistant_sessions")
