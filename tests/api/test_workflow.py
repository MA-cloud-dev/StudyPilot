from app.core.workflow import ALLOWED_TRANSITIONS, can_transition
from app.schemas.enums import WorkflowStage


def test_workflow_transition_matrix_allows_expected_path() -> None:
    assert can_transition(WorkflowStage.ONBOARDING, WorkflowStage.PLANNING)
    assert can_transition(WorkflowStage.CHECKPOINT_TEST, WorkflowStage.UNIT_REVIEW)
    assert can_transition(WorkflowStage.FINAL_TEST, WorkflowStage.NEXT_CYCLE)


def test_workflow_transition_matrix_blocks_invalid_path() -> None:
    assert not can_transition(WorkflowStage.ONBOARDING, WorkflowStage.FINAL_TEST)
    assert not can_transition(WorkflowStage.UNIT_REVIEW, WorkflowStage.LEARNING)


def test_enum_values_are_snake_case() -> None:
    for members in ALLOWED_TRANSITIONS.keys():
        assert members.value == members.value.lower()
        assert "-" not in members.value
