from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.knowledge import KnowledgeAsset, KnowledgeAssetListResponse, KnowledgeSearchResponse
from app.services.runtime import build_runtime_services

router = APIRouter()


@router.post(
    "/assets",
    response_model=KnowledgeAssetListResponse,
    responses={400: {"model": ErrorResponse}, 415: {"model": ErrorResponse}},
)
async def upload_assets(
    files: list[UploadFile] = File(...),
    title: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> KnowledgeAssetListResponse:
    knowledge_service, _ = build_runtime_services(db)
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    return await knowledge_service.upload_assets(files, title=title, tags=tag_list)


@router.get("/assets", response_model=KnowledgeAssetListResponse)
def list_assets(db: Session = Depends(get_db)) -> KnowledgeAssetListResponse:
    knowledge_service, _ = build_runtime_services(db)
    return knowledge_service.list_assets()


@router.delete("/assets/{asset_id}", response_model=MessageResponse, responses={404: {"model": ErrorResponse}})
def delete_asset(asset_id: str, db: Session = Depends(get_db)) -> MessageResponse:
    knowledge_service, _ = build_runtime_services(db)
    knowledge_service.delete_asset(asset_id)
    return MessageResponse(message="Asset deleted.")


@router.post("/assets/{asset_id}/retry", response_model=KnowledgeAsset, responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def retry_asset(asset_id: str, db: Session = Depends(get_db)) -> KnowledgeAsset:
    knowledge_service, _ = build_runtime_services(db)
    return knowledge_service.retry_asset(asset_id)


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_assets(
    query: str = Query(...),
    top_k: int = Query(default=5, alias="topK"),
    tags: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
) -> KnowledgeSearchResponse:
    knowledge_service, _ = build_runtime_services(db)
    return knowledge_service.search_assets(query=query, top_k=top_k, tags=tags)
