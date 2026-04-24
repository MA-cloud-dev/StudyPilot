from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import StudyPilotModel
from app.schemas.enums import WorkflowStage


class AgentTask(StudyPilotModel):
    id: str
    target_agent: str
    task_type: str
    input_context: dict = Field(default_factory=dict)
    trigger_reason: str
    created_at: datetime


class AgentDecision(StudyPilotModel):
    id: str
    task_id: str
    decision_summary: str
    next_state: WorkflowStage
    artifacts: dict = Field(default_factory=dict)
    created_at: datetime


class WorkflowState(StudyPilotModel):
    id: str
    current_stage: WorkflowStage
    current_macro_plan_id: str | None = None
    current_micro_plan_id: str | None = None
    recent_assessment_id: str | None = None
    next_action: str
    stage_history: list[dict] = Field(default_factory=list)
    updated_at: datetime


class WorkflowAdvanceRequest(StudyPilotModel):
    next_stage: WorkflowStage
    reason: str
