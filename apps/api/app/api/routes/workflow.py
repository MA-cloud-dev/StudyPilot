from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ErrorResponse
from app.schemas.workflow import WorkflowAdvanceRequest, WorkflowState
from app.services.runtime import build_runtime_services

router = APIRouter()


@router.get("/current", response_model=WorkflowState)
def get_current_workflow(db: Session = Depends(get_db)) -> WorkflowState:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.get_current_workflow()


@router.post("/advance", response_model=WorkflowState, responses={409: {"model": ErrorResponse}})
def advance_workflow(payload: WorkflowAdvanceRequest, db: Session = Depends(get_db)) -> WorkflowState:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.advance_workflow(payload.next_stage, payload.reason)


@router.post("/proceed", response_model=WorkflowState, responses={409: {"model": ErrorResponse}})
def proceed_workflow(db: Session = Depends(get_db)) -> WorkflowState:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.proceed_workflow()
