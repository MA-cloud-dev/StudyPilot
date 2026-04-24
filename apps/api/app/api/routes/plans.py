from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.plan import (
    CurrentPlanResponse,
    PlanAssistantGenerateResponse,
    PlanAssistantMessageRequest,
    PlanAssistantMessageResponse,
    PlanAssistantSession,
    PlanDetailResponse,
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanListResponse,
)
from app.services.runtime import build_runtime_services

router = APIRouter()


@router.get("", response_model=PlanListResponse)
def list_plans(db: Session = Depends(get_db)) -> PlanListResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.list_plans()


@router.get("/current", response_model=CurrentPlanResponse)
def get_current_plan(db: Session = Depends(get_db)) -> CurrentPlanResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.get_current_plan()


@router.post("/generate", response_model=PlanGenerateResponse, responses={404: {"model": ErrorResponse}})
def generate_plan(payload: PlanGenerateRequest, db: Session = Depends(get_db)) -> PlanGenerateResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.run_plan_generation(payload)


@router.post("/{plan_id}/activate", response_model=CurrentPlanResponse, responses={404: {"model": ErrorResponse}})
def activate_plan(plan_id: str, db: Session = Depends(get_db)) -> CurrentPlanResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.activate_plan(plan_id)


@router.post("/assistant/sessions", response_model=PlanAssistantSession)
def create_plan_assistant_session(db: Session = Depends(get_db)) -> PlanAssistantSession:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.create_plan_assistant_session()


@router.post("/assistant/sessions/{session_id}/messages", response_model=PlanAssistantMessageResponse, responses={404: {"model": ErrorResponse}})
def send_plan_assistant_message(
    session_id: str,
    payload: PlanAssistantMessageRequest,
    db: Session = Depends(get_db),
) -> PlanAssistantMessageResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.send_plan_assistant_message(session_id, payload)


@router.post("/assistant/sessions/{session_id}/generate", response_model=PlanAssistantGenerateResponse, responses={404: {"model": ErrorResponse}})
def generate_plan_from_assistant(session_id: str, db: Session = Depends(get_db)) -> PlanAssistantGenerateResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.generate_plan_from_assistant(session_id)


@router.get("/{plan_id}", response_model=PlanDetailResponse, responses={404: {"model": ErrorResponse}})
def get_plan_detail(plan_id: str, db: Session = Depends(get_db)) -> PlanDetailResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.get_plan_detail(plan_id)


@router.delete("/{plan_id}", response_model=MessageResponse, responses={404: {"model": ErrorResponse}})
def delete_plan(plan_id: str, db: Session = Depends(get_db)) -> MessageResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.delete_plan(plan_id)


@router.post("/{plan_id}/recalculate", response_model=PlanGenerateResponse, responses={404: {"model": ErrorResponse}})
def recalculate_plan(plan_id: str, db: Session = Depends(get_db)) -> PlanGenerateResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.recalculate_plan(plan_id)
