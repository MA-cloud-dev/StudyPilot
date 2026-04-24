from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.assessment import Assessment, Evaluation, Question, Submission, SubmissionAnswer
from app.schemas.enums import AssessmentStatus, AssessmentType, PlanStatus, WorkflowStage
from app.schemas.learning import ConversationTurn, LearningSession
from app.schemas.plan import MacroPlan, MicroPlan
from app.schemas.workflow import WorkflowState


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_macro_plan(user_id: str, goal: str) -> MacroPlan:
    now = utcnow()
    macro_plan_id = str(uuid4())
    return MacroPlan(
        id=macro_plan_id,
        user_id=user_id,
        title="Phase 0 Study Plan",
        goal=goal,
        duration={"unit": "week", "value": 2},
        milestones=[
            {"title": "Set the baseline", "target": "Understand the study scope"},
            {"title": "Reach checkpoint", "target": "Finish the first guided session"},
        ],
        units=[{"id": "unit-1", "title": "Foundation", "objective": "Build vocabulary and concepts"}],
        status=PlanStatus.ACTIVE,
        version=1,
        created_at=now,
        updated_at=now,
    )


def build_micro_plan(macro_plan_id: str) -> MicroPlan:
    now = utcnow()
    return MicroPlan(
        id=str(uuid4()),
        macro_plan_id=macro_plan_id,
        unit_id="unit-1",
        title="Today's focused session",
        topics=["overview", "core concepts", "quick recap"],
        estimated_duration=45,
        tasks=[
            {"title": "Read the overview", "status": "pending"},
            {"title": "Ask one follow-up question", "status": "pending"},
        ],
        completion_criteria=["Can explain the main concept in one paragraph"],
        assessment_trigger={"type": "after_session_complete", "minimum_tasks": 2},
        status=PlanStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def build_learning_session(micro_plan_id: str) -> LearningSession:
    now = utcnow()
    return LearningSession(
        id=str(uuid4()),
        micro_plan_id=micro_plan_id,
        session_summary="Session started with the current micro plan scaffold.",
        conversation_turns=[
            ConversationTurn(role="assistant", message="Welcome to the StudyPilot workbench.", created_at=now)
        ],
        completion_signals=[],
        mastery_signals=["baseline_started"],
        started_at=now,
        ended_at=None,
        updated_at=now,
    )


def build_assessment(linked_plan_id: str, assessment_type: AssessmentType) -> Assessment:
    now = utcnow()
    assessment_id = str(uuid4())
    question = Question(
        id=str(uuid4()),
        assessment_id=assessment_id,
        question_type="single_choice",
        stem="Which statement best summarizes the current study objective?",
        options=["Build a baseline", "Skip planning", "Delete the assets"],
        reference_scope="current_micro_plan",
        expected_competency="Can identify the immediate learning goal",
    )
    return Assessment(
        id=assessment_id,
        type=assessment_type,
        scope="current_micro_plan",
        linked_plan_id=linked_plan_id,
        questions=[question],
        difficulty="medium",
        status=AssessmentStatus.GENERATED,
        created_at=now,
        updated_at=now,
    )


def build_submission(assessment_id: str, answers: list[SubmissionAnswer], uncertainties: list[str]) -> Submission:
    return Submission(
        id=str(uuid4()),
        assessment_id=assessment_id,
        answers=answers,
        uncertainties=uncertainties,
        submitted_at=utcnow(),
    )


def build_evaluation(submission_id: str, uncertainties: list[str]) -> Evaluation:
    return Evaluation(
        id=str(uuid4()),
        submission_id=submission_id,
        score=0.65 if uncertainties else 0.85,
        feedback="This is a deterministic stage-0 evaluation stub.",
        mistake_analysis=[{"area": "concept recall", "impact": "medium"}],
        recommendations=["Review the overview once more", "Proceed to the next checkpoint if confident"],
        created_at=utcnow(),
    )


def build_default_workflow() -> WorkflowState:
    return WorkflowState(
        id=str(uuid4()),
        current_stage=WorkflowStage.ONBOARDING,
        current_macro_plan_id=None,
        current_micro_plan_id=None,
        recent_assessment_id=None,
        next_action="Create your learner profile to unlock planning.",
        stage_history=[],
        updated_at=utcnow(),
    )
