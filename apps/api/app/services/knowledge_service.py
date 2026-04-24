from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.models import KnowledgeAssetEntity
from app.schemas.enums import KnowledgeAssetStatus
from app.schemas.knowledge import KnowledgeAsset, KnowledgeAssetListResponse, KnowledgeSearchResponse
from app.services.knowledge_parser import KnowledgeParser
from app.services.retrieval import RetrievalProvider
from app.services.utils import utcnow


class KnowledgeService:
    SUPPORTED_TYPES = {".pdf", ".md", ".txt"}

    def __init__(
        self,
        db: Session,
        settings: Settings,
        parser: KnowledgeParser,
        retrieval_provider: RetrievalProvider,
    ) -> None:
        self.db = db
        self.settings = settings
        self.parser = parser
        self.retrieval_provider = retrieval_provider

    async def upload_assets(
        self,
        files: list[UploadFile],
        *,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> KnowledgeAssetListResponse:
        if len(files) > self.settings.max_upload_batch_count:
            raise AppError(400, "BATCH_LIMIT_EXCEEDED", "Too many files uploaded in a single request.")

        total_bytes = self.current_storage_usage()
        created_assets: list[KnowledgeAsset] = []

        for file in files:
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in self.SUPPORTED_TYPES:
                raise AppError(415, "UNSUPPORTED_FORMAT", "Only .pdf, .md, and .txt files are supported.")

            content = await file.read()
            file_size = len(content)
            if file_size > self.settings.max_file_size_mb * 1024 * 1024:
                raise AppError(400, "FILE_TOO_LARGE", "File exceeds the configured upload size limit.")
            if total_bytes + file_size > self.settings.max_total_storage_mb * 1024 * 1024:
                raise AppError(400, "STORAGE_QUOTA_EXCEEDED", "Upload would exceed the configured storage quota.")

            asset = self._create_asset(file.filename, suffix, file_size, title, tags or [])
            self.db.add(asset)
            self.db.flush()

            raw_path = self.settings.storage_raw_dir / f"{asset.id}{suffix}"
            raw_path.write_bytes(content)
            asset.raw_path = str(raw_path)

            parse_result = self._parse_and_index_asset(asset, raw_path)
            if parse_result.ok:
                asset.status = KnowledgeAssetStatus.READY.value
                asset.parse_error_reason = None
            else:
                asset.status = KnowledgeAssetStatus.PARSE_FAILED.value
                asset.parse_error_reason = parse_result.error_reason.value
                asset.chunks = []
            asset.updated_at = utcnow()

            created_assets.append(KnowledgeAsset.model_validate(asset))
            total_bytes += file_size

        self.db.commit()
        return KnowledgeAssetListResponse(assets=created_assets)

    def list_assets(self) -> KnowledgeAssetListResponse:
        assets = self.db.scalars(select(KnowledgeAssetEntity).where(KnowledgeAssetEntity.deleted_at.is_(None))).all()
        return KnowledgeAssetListResponse(assets=[KnowledgeAsset.model_validate(asset) for asset in assets])

    def delete_asset(self, asset_id: str) -> None:
        asset = self.db.get(KnowledgeAssetEntity, asset_id)
        if asset is None or asset.deleted_at is not None:
            raise AppError(404, "ASSET_NOT_FOUND", "Knowledge asset does not exist.")
        asset.deleted_at = utcnow()
        asset.updated_at = asset.deleted_at
        self.db.commit()

    def retry_asset(self, asset_id: str) -> KnowledgeAsset:
        asset = self.db.get(KnowledgeAssetEntity, asset_id)
        if asset is None:
            raise AppError(404, "ASSET_NOT_FOUND", "Knowledge asset does not exist.")
        if asset.status != KnowledgeAssetStatus.PARSE_FAILED.value:
            raise AppError(409, "ASSET_NOT_RETRYABLE", "Only parse_failed assets can be retried.")
        if asset.retry_count >= 1:
            raise AppError(409, "RETRY_LIMIT_EXCEEDED", "Automatic retry limit has already been used.")

        asset.retry_count += 1
        asset.status = KnowledgeAssetStatus.PARSING.value
        result = self._parse_and_index_asset(asset, Path(asset.raw_path))
        if result.ok:
            asset.status = KnowledgeAssetStatus.READY.value
            asset.parse_error_reason = None
        else:
            asset.status = KnowledgeAssetStatus.PARSE_FAILED.value
            asset.parse_error_reason = result.error_reason.value
        asset.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(asset)
        return KnowledgeAsset.model_validate(asset)

    def search_assets(self, query: str, top_k: int, tags: list[str] | None = None) -> KnowledgeSearchResponse:
        return KnowledgeSearchResponse(chunks=self.retrieval_provider.search(query, top_k=top_k, tags=tags))

    def current_storage_usage(self) -> int:
        assets = self.db.scalars(select(KnowledgeAssetEntity).where(KnowledgeAssetEntity.deleted_at.is_(None))).all()
        return sum(asset.file_size_bytes for asset in assets)

    def fetch_ready_assets(self, asset_ids: list[str] | None = None) -> list[KnowledgeAssetEntity]:
        stmt = select(KnowledgeAssetEntity).where(KnowledgeAssetEntity.deleted_at.is_(None)).where(
            KnowledgeAssetEntity.status == KnowledgeAssetStatus.READY.value
        )
        assets = list(self.db.scalars(stmt).all())
        if asset_ids:
            allowed = set(asset_ids)
            return [asset for asset in assets if asset.id in allowed]
        return assets

    def _create_asset(
        self,
        filename: str | None,
        suffix: str,
        file_size: int,
        title: str | None,
        tags: list[str],
    ) -> KnowledgeAssetEntity:
        now = utcnow()
        asset_id = str(uuid4())
        return KnowledgeAssetEntity(
            id=asset_id,
            title=title or filename or f"asset-{asset_id}",
            source_type="upload",
            file_type=suffix,
            file_size_bytes=file_size,
            status=KnowledgeAssetStatus.UPLOADING.value,
            parse_error_reason=None,
            retry_count=0,
            raw_path="",
            parsed_text="",
            tags=tags,
            chunks=[],
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    def _parse_and_index_asset(self, asset: KnowledgeAssetEntity, raw_path: Path):
        asset.status = KnowledgeAssetStatus.PARSING.value
        parse_result = self.parser.parse(raw_path, asset.file_type)
        parsed_output = self.settings.storage_parsed_dir / f"{asset.id}.txt"
        if not parse_result.ok:
            asset.parsed_text = ""
            if parsed_output.exists():
                parsed_output.unlink()
            return parse_result

        asset.parsed_text = parse_result.text
        parsed_output.write_text(parse_result.text, encoding="utf-8")
        asset.status = KnowledgeAssetStatus.INDEXING.value
        self.retrieval_provider.index_asset(asset, parse_result.text)
        return parse_result
