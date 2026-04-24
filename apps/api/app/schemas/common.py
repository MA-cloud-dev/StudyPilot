from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StudyPilotModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ErrorResponse(StudyPilotModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(StudyPilotModel):
    message: str


class ChunkSearchResult(StudyPilotModel):
    asset_id: str
    chunk_id: str
    content: str
    score: float


class TimestampedModel(StudyPilotModel):
    created_at: datetime
    updated_at: datetime
