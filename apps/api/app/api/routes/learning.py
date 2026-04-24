from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.learning import (
    LearningSessionCompleteRequest,
    LearningSessionMessageRequest,
    LearningSessionMessageResponse,
    LearningSessionStartRequest,
    LearningSession,
)
from app.services.runtime import build_runtime_services

router = APIRouter()


@router.post("/start", response_model=LearningSession, responses={404: {"model": ErrorResponse}})
def start_session(payload: LearningSessionStartRequest, db: Session = Depends(get_db)) -> LearningSession:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.start_learning_session(payload)


@router.post("/message", response_model=LearningSessionMessageResponse, responses={404: {"model": ErrorResponse}})
def send_message(payload: LearningSessionMessageRequest, db: Session = Depends(get_db)) -> LearningSessionMessageResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.run_learning_message(payload)


@router.post("/complete", response_model=MessageResponse, responses={404: {"model": ErrorResponse}})
def complete_session(payload: LearningSessionCompleteRequest, db: Session = Depends(get_db)) -> MessageResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.complete_learning_session(payload)
