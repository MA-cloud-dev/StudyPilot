from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


def generate_id() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserProfileEntity(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    learning_goals: Mapped[str] = mapped_column(Text, nullable=False)
    subject_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    current_level: Mapped[str] = mapped_column(String(64), nullable=False)
    time_budget: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    preferred_style: Mapped[str] = mapped_column(String(64), nullable=False)
    preferred_difficulty: Mapped[str] = mapped_column(String(64), nullable=False)
    preferred_question_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    behavior_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")


class KnowledgeAssetEntity(Base):
    __tablename__ = "knowledge_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    parse_error_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_path: Mapped[str] = mapped_column(String(512), nullable=False)
    parsed_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    chunks: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeChunkEntity(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_assets.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MacroPlanEntity(Base, TimestampMixin):
    __tablename__ = "macro_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_profiles.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    duration: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    milestones: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    units: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MicroPlanEntity(Base, TimestampMixin):
    __tablename__ = "micro_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    macro_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("macro_plans.id"), nullable=False)
    unit_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    topics: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=False)
    tasks: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    completion_criteria: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assessment_trigger: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LearningSessionEntity(Base):
    __tablename__ = "learning_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    micro_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("micro_plans.id"), nullable=False)
    session_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    conversation_turns: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    completion_signals: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    mastery_signals: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PlanAssistantSessionEntity(Base, TimestampMixin):
    __tablename__ = "plan_assistant_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    conversation_turns: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    conversation_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class AssessmentEntity(Base, TimestampMixin):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    linked_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("micro_plans.id"), nullable=False)
    questions: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class SubmissionEntity(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("assessments.id"), nullable=False)
    answers: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    uncertainties: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvaluationEntity(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    submission_id: Mapped[str] = mapped_column(String(36), ForeignKey("submissions.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    earned_points: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_points: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    passed: Mapped[bool] = mapped_column(nullable=False, default=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    mistake_analysis: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    question_results: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowStateEntity(Base):
    __tablename__ = "workflow_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    current_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    current_macro_plan_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("macro_plans.id"), nullable=True)
    current_micro_plan_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("micro_plans.id"), nullable=True)
    recent_assessment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assessments.id"), nullable=True)
    next_action: Mapped[str] = mapped_column(String(255), nullable=False)
    stage_history: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentTaskEntity(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    target_agent: Mapped[str] = mapped_column(String(64), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    input_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentDecisionEntity(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=False)
    decision_summary: Mapped[str] = mapped_column(Text, nullable=False)
    next_state: Mapped[str] = mapped_column(String(32), nullable=False)
    artifacts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
