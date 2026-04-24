from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import StudyPilotModel


class UserProfileBase(StudyPilotModel):
    learning_goals: str
    subject_scope: str
    current_level: str
    time_budget: dict[str, str | int]
    preferred_style: str
    preferred_difficulty: str
    preferred_question_types: list[str] = Field(default_factory=list)
    behavior_summary: str = ""


class UserProfileCreate(UserProfileBase):
    pass


class UserProfile(UserProfileBase):
    id: str
    created_at: datetime
    updated_at: datetime
