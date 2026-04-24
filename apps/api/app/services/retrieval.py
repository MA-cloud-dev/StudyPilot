from __future__ import annotations

from collections import Counter

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import KnowledgeAssetEntity, KnowledgeChunkEntity
from app.schemas.common import ChunkSearchResult
from app.services.chunking import ChunkingService
from app.services.llm_provider import LLMProviderAdapter
from app.services.utils import cosine_similarity, utcnow


class RetrievalProvider:
    def __init__(self, db: Session, llm_provider: LLMProviderAdapter, chunking_service: ChunkingService) -> None:
        self.db = db
        self.llm_provider = llm_provider
        self.chunking_service = chunking_service

    def index_asset(self, asset: KnowledgeAssetEntity, parsed_text: str) -> list[KnowledgeChunkEntity]:
        now = utcnow()
        documents = self.chunking_service.split(parsed_text)
        embeddings = self.llm_provider.embed_texts([document.content for document in documents]) if documents else []
        self.db.execute(delete(KnowledgeChunkEntity).where(KnowledgeChunkEntity.asset_id == asset.id))

        chunk_entities: list[KnowledgeChunkEntity] = []
        for document, embedding in zip(documents, embeddings, strict=False):
            chunk_entities.append(
                KnowledgeChunkEntity(
                    id=f"{asset.id}-chunk-{document.chunk_index + 1}",
                    asset_id=asset.id,
                    chunk_index=document.chunk_index,
                    content=document.content,
                    embedding=embedding,
                    chunk_metadata=document.metadata,
                    created_at=now,
                    updated_at=now,
                )
            )
        if chunk_entities:
            self.db.add_all(chunk_entities)
        asset.chunks = [
            {"id": chunk.id, "content": chunk.content, "embedding_id": f"embedding:{chunk.id}"}
            for chunk in chunk_entities
        ]
        asset.updated_at = now
        return chunk_entities

    def search(
        self,
        query: str,
        *,
        top_k: int,
        tags: list[str] | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[ChunkSearchResult]:
        if not query.strip():
            return []
        query_embedding = self.llm_provider.embed_texts([query])[0]
        query_terms = self._token_counts(query)

        stmt = (
            select(KnowledgeChunkEntity, KnowledgeAssetEntity)
            .join(KnowledgeAssetEntity, KnowledgeChunkEntity.asset_id == KnowledgeAssetEntity.id)
            .where(KnowledgeAssetEntity.deleted_at.is_(None))
            .where(KnowledgeAssetEntity.status == "ready")
        )
        rows = self.db.execute(stmt).all()

        results: list[ChunkSearchResult] = []
        for chunk, asset in rows:
            if tags and not set(tags).issubset(set(asset.tags)):
                continue
            if asset_ids and asset.id not in asset_ids:
                continue
            keyword_score = self._keyword_score(query_terms, chunk.content, asset.title)
            vector_score = cosine_similarity(query_embedding, list(chunk.embedding))
            score = (keyword_score * 0.55) + (max(vector_score, 0.0) * 0.45)
            if score <= 0:
                continue
            results.append(
                ChunkSearchResult(
                    asset_id=asset.id,
                    chunk_id=chunk.id,
                    content=chunk.content,
                    score=round(score, 4),
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    def list_chunks(self, asset_id: str) -> list[KnowledgeChunkEntity]:
        stmt = select(KnowledgeChunkEntity).where(KnowledgeChunkEntity.asset_id == asset_id).order_by(KnowledgeChunkEntity.chunk_index)
        return list(self.db.scalars(stmt).all())

    @staticmethod
    def _token_counts(text: str) -> Counter[str]:
        tokens = [token for token in "".join(char.lower() if char.isalnum() else " " for char in text).split() if token]
        return Counter(tokens)

    def _keyword_score(self, query_terms: Counter[str], content: str, title: str) -> float:
        corpus_terms = self._token_counts(f"{title} {content}")
        overlap = sum(min(query_terms[token], corpus_terms.get(token, 0)) for token in query_terms)
        denominator = max(1, sum(query_terms.values()))
        return overlap / denominator
