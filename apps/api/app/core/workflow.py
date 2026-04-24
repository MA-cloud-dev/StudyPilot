from __future__ import annotations

from app.schemas.enums import WorkflowStage

ALLOWED_TRANSITIONS: dict[WorkflowStage, set[WorkflowStage]] = {
    WorkflowStage.ONBOARDING: {WorkflowStage.PLANNING},
    WorkflowStage.PLANNING: {WorkflowStage.LEARNING},
    WorkflowStage.LEARNING: {WorkflowStage.CHECKPOINT_TEST},
    WorkflowStage.CHECKPOINT_TEST: {WorkflowStage.LEARNING, WorkflowStage.UNIT_REVIEW, WorkflowStage.NEXT_CYCLE},
    WorkflowStage.UNIT_REVIEW: {WorkflowStage.UNIT_TEST},
    WorkflowStage.UNIT_TEST: {WorkflowStage.LEARNING, WorkflowStage.FINAL_REVIEW},
    WorkflowStage.FINAL_REVIEW: {WorkflowStage.FINAL_TEST},
    WorkflowStage.FINAL_TEST: {WorkflowStage.LEARNING, WorkflowStage.NEXT_CYCLE},
    WorkflowStage.NEXT_CYCLE: {WorkflowStage.PLANNING},
}


def can_transition(current_stage: WorkflowStage, next_stage: WorkflowStage) -> bool:
    return next_stage in ALLOWED_TRANSITIONS.get(current_stage, set())
