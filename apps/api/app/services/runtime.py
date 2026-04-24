from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.chunking import ChunkingService
from app.services.knowledge_parser import KnowledgeParser
from app.services.knowledge_service import KnowledgeService
from app.services.llm_provider import build_llm_provider
from app.services.retrieval import RetrievalProvider
from app.services.scoring import ScoringService
from app.services.workflow_orchestrator import WorkflowOrchestrator


def build_runtime_services(db: Session) -> tuple[KnowledgeService, WorkflowOrchestrator]:
    settings = get_settings()
    llm_provider = build_llm_provider(settings)
    chunking_service = ChunkingService(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    retrieval_provider = RetrievalProvider(db=db, llm_provider=llm_provider, chunking_service=chunking_service)
    knowledge_service = KnowledgeService(
        db=db,
        settings=settings,
        parser=KnowledgeParser(),
        retrieval_provider=retrieval_provider,
    )
    orchestrator = WorkflowOrchestrator(
        db=db,
        settings=settings,
        llm_provider=llm_provider,
        retrieval_provider=retrieval_provider,
        knowledge_service=knowledge_service,
        scoring_service=ScoringService(llm_provider=llm_provider),
    )
    return knowledge_service, orchestrator
