from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import StudyPilotModel
from app.schemas.enums import PlanStatus
from app.schemas.learning import ConversationTurn


class MacroPlan(StudyPilotModel):
    id: str
    user_id: str
    title: str
    goal: str
    duration: dict[str, str | int]
    milestones: list[dict] = Field(default_factory=list)
    units: list[dict] = Field(default_factory=list)
    status: PlanStatus
    version: int
    created_at: datetime
    updated_at: datetime


class MicroPlan(StudyPilotModel):
    id: str
    macro_plan_id: str
    unit_id: str
    title: str
    topics: list[str] = Field(default_factory=list)
    estimated_duration: int
    tasks: list[dict] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)
    assessment_trigger: dict[str, str | int]
    status: PlanStatus
    created_at: datetime
    updated_at: datetime


class PlanGenerateRequest(StudyPilotModel):
    learning_goals: str
    time_budget: dict[str, str | int]
    current_level: str
    preferred_style: str
    preferred_difficulty: str
    preferred_question_types: list[str] = Field(default_factory=list)
    attached_asset_ids: list[str] = Field(default_factory=list)


class PlanGenerateResponse(StudyPilotModel):
    macro_plan: MacroPlan
    current_micro_plan: MicroPlan


class CurrentPlanResponse(StudyPilotModel):
    macro_plan: MacroPlan | None = None
    current_micro_plan: MicroPlan | None = None


class PlanCardSummary(StudyPilotModel):
    id: str
    title: str
    goal: str
    status: PlanStatus
    version: int
    created_at: datetime
    updated_at: datetime
    unit_count: int
    completed_unit_count: int
    progress_percent: int
    current_micro_plan_id: str | None = None
    current_micro_plan_title: str | None = None
    is_current: bool = False


class PlanListResponse(StudyPilotModel):
    plans: list[PlanCardSummary] = Field(default_factory=list)


class PlanDetailResponse(StudyPilotModel):
    macro_plan: MacroPlan
    micro_plans: list[MicroPlan] = Field(default_factory=list)
    current_micro_plan_id: str | None = None
    is_current: bool = False


class PlanAssistantSession(StudyPilotModel):
    id: str
    conversation_turns: list[ConversationTurn] = Field(default_factory=list)
    conversation_summary: str
    status: str
    created_at: datetime
    updated_at: datetime


class PlanAssistantMessageRequest(StudyPilotModel):
    message: str


class PlanAssistantMessageResponse(StudyPilotModel):
    reply: str
    session: PlanAssistantSession


class PlanAssistantGenerateResponse(StudyPilotModel):
    session: PlanAssistantSession
    macro_plan: MacroPlan
    current_micro_plan: MicroPlan
