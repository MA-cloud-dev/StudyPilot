"""phase 1 knowledge chunk storage"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_0002"
down_revision = "20260331_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("knowledge_assets.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_asset_id", "knowledge_chunks", ["asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_asset_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
