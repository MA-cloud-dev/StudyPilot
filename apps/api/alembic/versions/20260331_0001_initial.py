"""initial phase 0 schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("learning_goals", sa.Text(), nullable=False),
        sa.Column("subject_scope", sa.String(length=255), nullable=False),
        sa.Column("current_level", sa.String(length=64), nullable=False),
        sa.Column("time_budget", sa.JSON(), nullable=False),
        sa.Column("preferred_style", sa.String(length=64), nullable=False),
        sa.Column("preferred_difficulty", sa.String(length=64), nullable=False),
        sa.Column("preferred_question_types", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("behavior_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "knowledge_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("parse_error_reason", sa.String(length=64), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_path", sa.String(length=512), nullable=False),
        sa.Column("parsed_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("chunks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "macro_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("duration", sa.JSON(), nullable=False),
        sa.Column("milestones", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("units", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "micro_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("macro_plan_id", sa.String(length=36), sa.ForeignKey("macro_plans.id"), nullable=False),
        sa.Column("unit_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("topics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("estimated_duration", sa.Integer(), nullable=False),
        sa.Column("tasks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("completion_criteria", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("assessment_trigger", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("micro_plan_id", sa.String(length=36), sa.ForeignKey("micro_plans.id"), nullable=False),
        sa.Column("session_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("conversation_turns", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("completion_signals", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("mastery_signals", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("linked_plan_id", sa.String(length=36), sa.ForeignKey("micro_plans.id"), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("assessment_id", sa.String(length=36), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("uncertainties", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "evaluations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("submission_id", sa.String(length=36), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("mistake_analysis", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("recommendations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "workflow_states",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("current_stage", sa.String(length=32), nullable=False),
        sa.Column("current_macro_plan_id", sa.String(length=36), sa.ForeignKey("macro_plans.id"), nullable=True),
        sa.Column("current_micro_plan_id", sa.String(length=36), sa.ForeignKey("micro_plans.id"), nullable=True),
        sa.Column("recent_assessment_id", sa.String(length=36), sa.ForeignKey("assessments.id"), nullable=True),
        sa.Column("next_action", sa.String(length=255), nullable=False),
        sa.Column("stage_history", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("target_agent", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("input_context", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("trigger_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "agent_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("agent_tasks.id"), nullable=False),
        sa.Column("decision_summary", sa.Text(), nullable=False),
        sa.Column("next_state", sa.String(length=32), nullable=False),
        sa.Column("artifacts", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_decisions")
    op.drop_table("agent_tasks")
    op.drop_table("workflow_states")
    op.drop_table("evaluations")
    op.drop_table("submissions")
    op.drop_table("assessments")
    op.drop_table("learning_sessions")
    op.drop_table("micro_plans")
    op.drop_table("macro_plans")
    op.drop_table("knowledge_assets")
    op.drop_table("user_profiles")
