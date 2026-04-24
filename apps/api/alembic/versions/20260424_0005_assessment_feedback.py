"""assessment feedback details"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_0005"
down_revision = "20260424_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evaluations", sa.Column("earned_points", sa.Float(), nullable=False, server_default="0"))
    op.add_column("evaluations", sa.Column("total_points", sa.Float(), nullable=False, server_default="0"))
    op.add_column("evaluations", sa.Column("score_ratio", sa.Float(), nullable=False, server_default="0"))
    op.add_column("evaluations", sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("evaluations", sa.Column("question_results", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("evaluations", "question_results")
    op.drop_column("evaluations", "passed")
    op.drop_column("evaluations", "score_ratio")
    op.drop_column("evaluations", "total_points")
    op.drop_column("evaluations", "earned_points")
