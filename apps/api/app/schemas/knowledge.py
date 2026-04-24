from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ChunkSearchResult, StudyPilotModel
from app.schemas.enums import KnowledgeAssetStatus, ParseErrorReason


class KnowledgeChunk(StudyPilotModel):
    id: str
    content: str
    embedding_id: str | None = None


class KnowledgeAsset(StudyPilotModel):
    id: str
    title: str
    source_type: str
    file_type: str
    file_size_bytes: int
    status: KnowledgeAssetStatus
    parse_error_reason: ParseErrorReason | None = None
    retry_count: int = 0
    raw_path: str
    parsed_text: str = ""
    tags: list[str] = Field(default_factory=list)
    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class KnowledgeAssetListResponse(StudyPilotModel):
    assets: list[KnowledgeAsset]


class KnowledgeSearchResponse(StudyPilotModel):
    chunks: list[ChunkSearchResult]
