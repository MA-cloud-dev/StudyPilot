from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.enums import KnowledgeAssetStatus, ParseErrorReason
from app.schemas.knowledge import KnowledgeAsset


def test_knowledge_asset_schema_accepts_parse_failed_payload() -> None:
    asset = KnowledgeAsset(
        id="asset-1",
        title="Empty file",
        source_type="upload",
        file_type=".md",
        file_size_bytes=0,
        status=KnowledgeAssetStatus.PARSE_FAILED,
        parse_error_reason=ParseErrorReason.EMPTY_CONTENT,
        retry_count=0,
        raw_path="storage/raw/asset-1.md",
        tags=[],
        chunks=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    assert asset.parse_error_reason == ParseErrorReason.EMPTY_CONTENT


def test_knowledge_asset_schema_requires_title() -> None:
    with pytest.raises(ValidationError):
        KnowledgeAsset(
            id="asset-1",
            title=None,
            source_type="upload",
            file_type=".md",
            file_size_bytes=0,
            status=KnowledgeAssetStatus.PARSE_FAILED,
            parse_error_reason=ParseErrorReason.EMPTY_CONTENT,
            retry_count=0,
            raw_path="storage/raw/asset-1.md",
            tags=[],
            chunks=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
