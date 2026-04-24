from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.assessment import (
    Assessment,
    AssessmentGenerateRequest,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
    Evaluation,
)
from app.schemas.common import ErrorResponse
from app.services.runtime import build_runtime_services

router = APIRouter()


@router.get("/{assessment_id}", response_model=Assessment, responses={404: {"model": ErrorResponse}})
def get_assessment(assessment_id: str, db: Session = Depends(get_db)) -> Assessment:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.get_assessment(assessment_id)


@router.post("/generate", response_model=Assessment, responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def generate_assessment(payload: AssessmentGenerateRequest, db: Session = Depends(get_db)) -> Assessment:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.run_assessment_generation(payload)


@router.post("/{assessment_id}/submit", response_model=AssessmentSubmitResponse, responses={404: {"model": ErrorResponse}})
def submit_assessment(assessment_id: str, payload: AssessmentSubmitRequest, db: Session = Depends(get_db)) -> AssessmentSubmitResponse:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.run_assessment_evaluation(assessment_id, payload)


@router.get("/{assessment_id}/result", response_model=Evaluation, responses={404: {"model": ErrorResponse}})
def get_assessment_result(assessment_id: str, db: Session = Depends(get_db)) -> Evaluation:
    _, orchestrator = build_runtime_services(db)
    return orchestrator.get_assessment_result(assessment_id)
