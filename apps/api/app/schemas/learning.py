from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import StudyPilotModel


class ConversationTurn(StudyPilotModel):
    role: str
    message: str
    created_at: datetime


class LearningSession(StudyPilotModel):
    id: str
    micro_plan_id: str
    session_summary: str
    conversation_turns: list[ConversationTurn] = Field(default_factory=list)
    completion_signals: list[str] = Field(default_factory=list)
    mastery_signals: list[str] = Field(default_factory=list)
    started_at: datetime
    ended_at: datetime | None = None
    updated_at: datetime


class LearningSessionStartRequest(StudyPilotModel):
    micro_plan_id: str


class LearningSessionMessageRequest(StudyPilotModel):
    session_id: str
    message: str
    preferred_style: str | None = None


class LearningSessionMessageResponse(StudyPilotModel):
    reply: str
    session_summary: str
    mastery_signals: list[str] = Field(default_factory=list)


class LearningSessionCompleteRequest(StudyPilotModel):
    session_id: str
    completion_signals: list[str] = Field(default_factory=list)
