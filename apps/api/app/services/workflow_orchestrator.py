from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.workflow import can_transition
from app.models import (
    AgentDecisionEntity,
    AgentTaskEntity,
    AssessmentEntity,
    EvaluationEntity,
    LearningSessionEntity,
    MacroPlanEntity,
    MicroPlanEntity,
    PlanAssistantSessionEntity,
    SubmissionEntity,
    UserProfileEntity,
    WorkflowStateEntity,
)
from app.schemas.assessment import (
    Assessment,
    AssessmentGenerateRequest,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
    Evaluation,
    Submission,
)
from app.schemas.common import MessageResponse
from app.schemas.enums import AssessmentStatus, AssessmentType, PlanStatus, WorkflowStage
from app.schemas.learning import (
    LearningSession,
    LearningSessionCompleteRequest,
    LearningSessionMessageRequest,
    LearningSessionMessageResponse,
    LearningSessionStartRequest,
)
from app.schemas.plan import (
    CurrentPlanResponse,
    MacroPlan,
    MicroPlan,
    PlanAssistantGenerateResponse,
    PlanAssistantMessageRequest,
    PlanAssistantMessageResponse,
    PlanAssistantSession,
    PlanCardSummary,
    PlanDetailResponse,
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanListResponse,
)
from app.schemas.workflow import WorkflowState
from app.services.knowledge_service import KnowledgeService
from app.services.llm_provider import LLMProviderAdapter
from app.services.retrieval import RetrievalProvider
from app.services.scoring import ScoringOutcome, ScoringService
from app.services.utils import utcnow

try:  # pragma: no cover
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover
    END = START = None
    StateGraph = None


ASSESSMENT_STAGE_BY_TYPE: dict[AssessmentType, WorkflowStage] = {
    AssessmentType.CHECKPOINT: WorkflowStage.CHECKPOINT_TEST,
    AssessmentType.UNIT: WorkflowStage.UNIT_TEST,
    AssessmentType.FINAL: WorkflowStage.FINAL_TEST,
}


@dataclass(slots=True)
class OrchestrationResult:
    payload: dict[str, Any]
    next_stage: WorkflowStage
    summary: str


class WorkflowOrchestrator:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        llm_provider: LLMProviderAdapter,
        retrieval_provider: RetrievalProvider,
        knowledge_service: KnowledgeService,
        scoring_service: ScoringService,
    ) -> None:
        self.db = db
        self.settings = settings
        self.llm_provider = llm_provider
        self.retrieval_provider = retrieval_provider
        self.knowledge_service = knowledge_service
        self.scoring_service = scoring_service

    def get_current_plan(self) -> CurrentPlanResponse:
        workflow = self.db.scalar(select(WorkflowStateEntity).limit(1))
        macro = self._get_visible_macro_plan(workflow.current_macro_plan_id) if workflow and workflow.current_macro_plan_id else None
        micro = self._get_visible_micro_plan(workflow.current_micro_plan_id) if workflow and workflow.current_micro_plan_id else None
        if macro is None:
            macro = self._latest_visible_macro_plan()
        if micro is None and macro is not None:
            micro = self._resolve_display_micro_plan(macro.id)
        return CurrentPlanResponse(
            macro_plan=MacroPlan.model_validate(macro) if macro else None,
            current_micro_plan=MicroPlan.model_validate(micro) if micro else None,
        )

    def list_plans(self) -> PlanListResponse:
        workflow = self.db.scalar(select(WorkflowStateEntity).limit(1))
        macros = list(
            self.db.scalars(
                select(MacroPlanEntity).where(MacroPlanEntity.deleted_at.is_(None)).order_by(desc(MacroPlanEntity.updated_at))
            ).all()
        )
        micro_plans = list(
            self.db.scalars(
                select(MicroPlanEntity).where(MicroPlanEntity.deleted_at.is_(None)).order_by(desc(MicroPlanEntity.created_at))
            ).all()
        )
        micro_plans_by_macro: dict[str, list[MicroPlanEntity]] = {}
        for micro_plan in micro_plans:
            micro_plans_by_macro.setdefault(micro_plan.macro_plan_id, []).append(micro_plan)

        summaries = [
            self._build_plan_card_summary(
                macro_plan,
                micro_plans_by_macro.get(macro_plan.id, []),
                workflow,
            )
            for macro_plan in macros
        ]
        summaries.sort(key=lambda item: (not item.is_current, -item.updated_at.timestamp(), -item.version))
        return PlanListResponse(plans=summaries)

    def get_plan_detail(self, plan_id: str) -> PlanDetailResponse:
        macro_plan = self._get_visible_macro_plan(plan_id)
        if macro_plan is None:
            raise AppError(404, "PLAN_NOT_FOUND", "Macro plan does not exist.")

        workflow = self.db.scalar(select(WorkflowStateEntity).limit(1))
        micro_plans = list(
            self.db.scalars(
                select(MicroPlanEntity)
                .where(MicroPlanEntity.macro_plan_id == plan_id)
                .where(MicroPlanEntity.deleted_at.is_(None))
            ).all()
        )
        ordered_micro_plans = sorted(micro_plans, key=lambda item: self._micro_plan_sort_key(macro_plan, item))
        is_current = bool(workflow and workflow.current_macro_plan_id == macro_plan.id)
        current_micro_plan_id = workflow.current_micro_plan_id if is_current else None

        return PlanDetailResponse(
            macro_plan=MacroPlan.model_validate(macro_plan),
            micro_plans=[MicroPlan.model_validate(micro_plan) for micro_plan in ordered_micro_plans],
            current_micro_plan_id=current_micro_plan_id,
            is_current=is_current,
        )

    def activate_plan(self, plan_id: str) -> CurrentPlanResponse:
        macro_plan = self._get_visible_macro_plan(plan_id)
        if macro_plan is None:
            raise AppError(404, "PLAN_NOT_FOUND", "Macro plan does not exist.")

        workflow = self._ensure_workflow()
        target_micro_plan = self._resolve_display_micro_plan(plan_id)
        workflow.current_macro_plan_id = macro_plan.id
        workflow.current_micro_plan_id = target_micro_plan.id if target_micro_plan else None
        workflow.recent_assessment_id = None
        self._transition_workflow(
            workflow,
            WorkflowStage.LEARNING,
            f"Current plan switched to {macro_plan.title}.",
            validate=False,
        )
        self.db.commit()

        return CurrentPlanResponse(
            macro_plan=MacroPlan.model_validate(macro_plan),
            current_micro_plan=MicroPlan.model_validate(target_micro_plan) if target_micro_plan else None,
        )

    def delete_plan(self, plan_id: str) -> MessageResponse:
        macro_plan = self._get_visible_macro_plan(plan_id)
        if macro_plan is None:
            raise AppError(404, "PLAN_NOT_FOUND", "Macro plan does not exist.")

        now = utcnow()
        micro_plans = list(
            self.db.scalars(select(MicroPlanEntity).where(MicroPlanEntity.macro_plan_id == plan_id)).all()
        )
        macro_plan.deleted_at = now
        macro_plan.updated_at = now
        for micro_plan in micro_plans:
            micro_plan.deleted_at = now
            micro_plan.updated_at = now

        workflow = self.db.scalar(select(WorkflowStateEntity).limit(1))
        if workflow and workflow.current_macro_plan_id == plan_id:
            fallback_macro_plan = self._latest_visible_macro_plan(exclude_plan_id=plan_id)
            if fallback_macro_plan is not None:
                fallback_micro_plan = self._resolve_display_micro_plan(fallback_macro_plan.id)
                workflow.current_macro_plan_id = fallback_macro_plan.id
                workflow.current_micro_plan_id = fallback_micro_plan.id if fallback_micro_plan else None
                workflow.recent_assessment_id = None
                self._transition_workflow(
                    workflow,
                    WorkflowStage.LEARNING,
                    f"Current plan deleted. Switched to {fallback_macro_plan.title}.",
                    validate=False,
                )
            else:
                workflow.current_macro_plan_id = None
                workflow.current_micro_plan_id = None
                workflow.recent_assessment_id = None
                self._transition_workflow(
                    workflow,
                    WorkflowStage.PLANNING,
                    "Current plan deleted. Create a new plan to continue learning.",
                    validate=False,
                )

        self.db.commit()
        return MessageResponse(message="Plan deleted.")

    def create_plan_assistant_session(self) -> PlanAssistantSession:
        now = utcnow()
        greeting = (
            "告诉我你想学什么、想达到什么结果，"
            "如果愿意也可以补充当前基础、目标时间或学习节奏，我会帮你整理成学习计划。"
        )
        session = PlanAssistantSessionEntity(
            id=str(uuid4()),
            conversation_turns=[{"role": "assistant", "message": greeting, "created_at": now.isoformat()}],
            conversation_summary="",
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return PlanAssistantSession.model_validate(session)

    def send_plan_assistant_message(self, session_id: str, payload: PlanAssistantMessageRequest) -> PlanAssistantMessageResponse:
        session = self.db.get(PlanAssistantSessionEntity, session_id)
        if session is None:
            raise AppError(404, "PLAN_ASSISTANT_SESSION_NOT_FOUND", "Plan assistant session does not exist.")

        previous_summary = session.conversation_summary
        response_payload = self.llm_provider.generate_structured(
            "plan_assistant_reply",
            {
                "message": payload.message,
                "conversation_summary": previous_summary,
            },
        )

        now = utcnow()
        turns = list(session.conversation_turns)
        turns.append({"role": "user", "message": payload.message, "created_at": now.isoformat()})
        turns.append({"role": "assistant", "message": response_payload["reply"], "created_at": now.isoformat()})
        session.conversation_turns = turns
        session.conversation_summary = str(response_payload["conversation_summary"]).strip()
        session.updated_at = now
        self.db.commit()
        self.db.refresh(session)
        return PlanAssistantMessageResponse(
            reply=response_payload["reply"],
            session=PlanAssistantSession.model_validate(session),
        )

    def generate_plan_from_assistant(self, session_id: str) -> PlanAssistantGenerateResponse:
        session = self.db.get(PlanAssistantSessionEntity, session_id)
        if session is None:
            raise AppError(404, "PLAN_ASSISTANT_SESSION_NOT_FOUND", "Plan assistant session does not exist.")

        profile = self.db.scalar(select(UserProfileEntity).limit(1))
        if profile is None:
            raise AppError(404, "PROFILE_NOT_FOUND", "Create a learner profile before generating a plan.")

        ready_assets = self.knowledge_service.fetch_ready_assets()
        request = self._build_plan_generation_request_from_assistant(session, profile, ready_assets)
        generated_plan = self.run_plan_generation(request)

        now = utcnow()
        session.conversation_turns = [
            *list(session.conversation_turns),
            {
                "role": "assistant",
                "message": f"已根据当前对话生成计划：{generated_plan.macro_plan.title}",
                "created_at": now.isoformat(),
            },
        ]
        session.conversation_summary = generated_plan.macro_plan.goal
        session.status = "generated"
        session.updated_at = now
        self.db.commit()
        self.db.refresh(session)

        return PlanAssistantGenerateResponse(
            session=PlanAssistantSession.model_validate(session),
            macro_plan=generated_plan.macro_plan,
            current_micro_plan=generated_plan.current_micro_plan,
        )

    def run_plan_generation(self, payload: PlanGenerateRequest) -> PlanGenerateResponse:
        profile = self.db.scalar(select(UserProfileEntity).limit(1))
        if profile is None:
            raise AppError(404, "PROFILE_NOT_FOUND", "Create a learner profile before generating a plan.")

        workflow = self._ensure_workflow()
        relevant_assets = self.knowledge_service.fetch_ready_assets(payload.attached_asset_ids)
        relevant_chunks = self.retrieval_provider.search(
            payload.learning_goals,
            top_k=self.settings.retrieval_top_k,
            asset_ids=[asset.id for asset in relevant_assets] or None,
        )
        result = self._run_graph(
            "plan_agent",
            "generate_plan",
            WorkflowStage.LEARNING,
            {
                "learning_goals": payload.learning_goals,
                "time_budget": payload.time_budget,
                "current_level": payload.current_level,
                "preferred_style": payload.preferred_style,
                "preferred_difficulty": payload.preferred_difficulty,
                "preferred_question_types": payload.preferred_question_types,
                "knowledge_assets": [{"id": asset.id, "title": asset.title} for asset in relevant_assets],
                "knowledge_chunks": [chunk.model_dump() for chunk in relevant_chunks],
            },
        )

        latest_plan = self.db.scalar(
            select(MacroPlanEntity).where(MacroPlanEntity.user_id == profile.id).order_by(desc(MacroPlanEntity.version)).limit(1)
        )
        version = (latest_plan.version + 1) if latest_plan else 1
        now = utcnow()
        macro_plan = MacroPlanEntity(
            id=str(uuid4()),
            user_id=profile.id,
            title=result.payload["macro_plan"]["title"],
            goal=result.payload["macro_plan"]["goal"],
            duration=result.payload["macro_plan"]["duration"],
            milestones=result.payload["macro_plan"]["milestones"],
            units=result.payload["macro_plan"]["units"],
            status=PlanStatus.ACTIVE.value,
            version=version,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        micro_payload = result.payload["micro_plan"]
        micro_plan = MicroPlanEntity(
            id=str(uuid4()),
            macro_plan_id=macro_plan.id,
            unit_id=micro_payload["unit_id"],
            title=micro_payload["title"],
            topics=micro_payload["topics"],
            estimated_duration=self._coerce_estimated_duration(micro_payload.get("estimated_duration"), payload.time_budget.get("value", 45)),
            tasks=micro_payload["tasks"],
            completion_criteria=micro_payload["completion_criteria"],
            assessment_trigger=micro_payload["assessment_trigger"],
            status=PlanStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        self.db.add_all([macro_plan, micro_plan])
        workflow.current_macro_plan_id = macro_plan.id
        workflow.current_micro_plan_id = micro_plan.id
        workflow.recent_assessment_id = None
        self._transition_workflow(workflow, WorkflowStage.PLANNING, "Planning artifacts are being prepared.", validate=False)
        self._transition_workflow(workflow, WorkflowStage.LEARNING, "Plan generated and learning can start now.", validate=False)
        self.db.commit()
        return PlanGenerateResponse(
            macro_plan=MacroPlan.model_validate(macro_plan),
            current_micro_plan=MicroPlan.model_validate(micro_plan),
        )

    def recalculate_plan(self, plan_id: str) -> PlanGenerateResponse:
        macro = self._get_visible_macro_plan(plan_id)
        if macro is None:
            raise AppError(404, "PLAN_NOT_FOUND", "Macro plan does not exist.")
        profile = self.db.scalar(select(UserProfileEntity).limit(1))
        if profile is None:
            raise AppError(404, "PROFILE_NOT_FOUND", "Create a learner profile before recalculating a plan.")
        request = PlanGenerateRequest(
            learning_goals=macro.goal,
            time_budget=macro.duration,
            current_level=profile.current_level,
            preferred_style=profile.preferred_style,
            preferred_difficulty=profile.preferred_difficulty,
            preferred_question_types=profile.preferred_question_types,
            attached_asset_ids=[],
        )
        response = self.run_plan_generation(request)
        macro.status = PlanStatus.COMPLETED.value
        macro.updated_at = utcnow()
        self.db.commit()
        return response

    def start_learning_session(self, payload: LearningSessionStartRequest) -> LearningSession:
        micro_plan = self.db.get(MicroPlanEntity, payload.micro_plan_id)
        if micro_plan is None or micro_plan.deleted_at is not None:
            raise AppError(404, "MICRO_PLAN_NOT_FOUND", "Micro plan does not exist.")
        now = utcnow()
        session = LearningSessionEntity(
            id=str(uuid4()),
            micro_plan_id=micro_plan.id,
            session_summary=f"Learning session started for {micro_plan.title}.",
            conversation_turns=[
                {"role": "assistant", "message": f"Let's work through {micro_plan.title} together.", "created_at": now.isoformat()}
            ],
            completion_signals=[],
            mastery_signals=["session_started"],
            started_at=now,
            ended_at=None,
            updated_at=now,
        )
        self.db.add(session)
        workflow = self._ensure_workflow()
        self._transition_workflow(workflow, WorkflowStage.LEARNING, f"Continue learning within {micro_plan.title}.", validate=False)
        self.db.commit()
        return LearningSession.model_validate(session)

    def run_learning_message(self, payload: LearningSessionMessageRequest) -> LearningSessionMessageResponse:
        session = self.db.get(LearningSessionEntity, payload.session_id)
        if session is None:
            raise AppError(404, "SESSION_NOT_FOUND", "Learning session does not exist.")
        micro_plan = self.db.get(MicroPlanEntity, session.micro_plan_id)
        if micro_plan is None or micro_plan.deleted_at is not None:
            raise AppError(404, "MICRO_PLAN_NOT_FOUND", "Micro plan does not exist.")

        result = self._run_graph(
            "input_agent",
            "learning_message",
            WorkflowStage.LEARNING,
            {
                "session_id": session.id,
                "message": payload.message,
                "preferred_style": payload.preferred_style,
                "micro_plan": {"id": micro_plan.id, "title": micro_plan.title, "topics": micro_plan.topics},
                "knowledge_chunks": [chunk.model_dump() for chunk in self.retrieval_provider.search(payload.message, top_k=2)],
            },
        )
        now = utcnow()
        turns = list(session.conversation_turns)
        turns.append({"role": "user", "message": payload.message, "created_at": now.isoformat()})
        turns.append({"role": "assistant", "message": result.payload["reply"], "created_at": now.isoformat()})
        session.conversation_turns = turns
        session.session_summary = result.payload["session_summary"]
        session.mastery_signals = list(dict.fromkeys([*session.mastery_signals, *result.payload["mastery_signals"]]))
        session.updated_at = now
        self.db.commit()
        return LearningSessionMessageResponse(
            reply=result.payload["reply"],
            session_summary=session.session_summary,
            mastery_signals=session.mastery_signals,
        )

    def complete_learning_session(self, payload: LearningSessionCompleteRequest) -> MessageResponse:
        session = self.db.get(LearningSessionEntity, payload.session_id)
        if session is None:
            raise AppError(404, "SESSION_NOT_FOUND", "Learning session does not exist.")
        now = utcnow()
        session.ended_at = now
        session.updated_at = now
        session.completion_signals = payload.completion_signals

        workflow = self._ensure_workflow()
        workflow.recent_assessment_id = None
        self._transition_workflow(workflow, WorkflowStage.CHECKPOINT_TEST, "Learning session completed. Generate a checkpoint assessment.")
        self.db.commit()
        return MessageResponse(message="Learning session completed.")

    def run_assessment_generation(self, payload: AssessmentGenerateRequest) -> Assessment:
        workflow = self._ensure_workflow()
        self._validate_assessment_type_for_stage(payload.type, WorkflowStage(workflow.current_stage))

        micro_plan = self.db.get(MicroPlanEntity, payload.linked_plan_id)
        if micro_plan is None or micro_plan.deleted_at is not None:
            raise AppError(404, "MICRO_PLAN_NOT_FOUND", "Micro plan does not exist.")
        result = self._run_graph(
            "output_agent",
            "generate_assessment",
            ASSESSMENT_STAGE_BY_TYPE[payload.type],
            {
                "linked_plan_id": payload.linked_plan_id,
                "assessment_type": payload.type.value,
                "workflow_stage": workflow.current_stage,
                "micro_plan": {"id": micro_plan.id, "title": micro_plan.title, "topics": micro_plan.topics},
                "knowledge_chunks": [chunk.model_dump() for chunk in self.retrieval_provider.search(" ".join(micro_plan.topics), top_k=2)],
            },
        )
        now = utcnow()
        assessment_id = str(uuid4())
        questions = [{"id": str(uuid4()), "assessment_id": assessment_id, **question} for question in result.payload["questions"]]
        entity = AssessmentEntity(
            id=assessment_id,
            type=payload.type.value,
            scope=result.payload["scope"],
            linked_plan_id=payload.linked_plan_id,
            questions=questions,
            difficulty=result.payload["difficulty"],
            status=AssessmentStatus.GENERATED.value,
            created_at=now,
            updated_at=now,
        )
        self.db.add(entity)
        workflow.recent_assessment_id = entity.id
        self._transition_workflow(workflow, ASSESSMENT_STAGE_BY_TYPE[payload.type], self._assessment_generation_reason(payload.type), validate=False)
        self.db.commit()
        return Assessment.model_validate(entity)

    def get_assessment(self, assessment_id: str) -> Assessment:
        assessment = self.db.get(AssessmentEntity, assessment_id)
        if assessment is None:
            raise AppError(404, "ASSESSMENT_NOT_FOUND", "Assessment does not exist.")
        return Assessment.model_validate(assessment)

    def run_assessment_evaluation(self, assessment_id: str, payload: AssessmentSubmitRequest) -> AssessmentSubmitResponse:
        assessment = self.db.get(AssessmentEntity, assessment_id)
        if assessment is None:
            raise AppError(404, "ASSESSMENT_NOT_FOUND", "Assessment does not exist.")
        submission = Submission(
            id=str(uuid4()),
            assessment_id=assessment_id,
            answers=payload.answers,
            uncertainties=payload.uncertainties,
            submitted_at=utcnow(),
        )
        outcome = self.scoring_service.evaluate(
            assessment.questions,
            payload.answers,
            payload.uncertainties,
            assessment_type=assessment.type,
            mastery_threshold=self.settings.assessment_mastery_threshold,
        )
        evaluation_model = self.scoring_service.build_evaluation(submission.id, outcome)

        self.db.add(SubmissionEntity(**submission.model_dump()))
        self.db.flush()
        self.db.add(EvaluationEntity(**evaluation_model.model_dump()))
        assessment.status = AssessmentStatus.EVALUATED.value
        assessment.updated_at = utcnow()

        workflow = self._ensure_workflow()
        workflow.recent_assessment_id = assessment_id
        next_stage, reason = self._apply_assessment_outcome(workflow, assessment, outcome, evaluation_model)
        self._transition_workflow(workflow, next_stage, reason)
        self.db.commit()
        return AssessmentSubmitResponse(submission=submission, evaluation=evaluation_model)

    def get_assessment_result(self, assessment_id: str) -> Evaluation:
        assessment = self.db.get(AssessmentEntity, assessment_id)
        if assessment is None:
            raise AppError(404, "ASSESSMENT_NOT_FOUND", "Assessment does not exist.")
        submission = self.db.scalar(
            select(SubmissionEntity).where(SubmissionEntity.assessment_id == assessment_id).order_by(desc(SubmissionEntity.submitted_at)).limit(1)
        )
        if submission is None:
            raise AppError(404, "SUBMISSION_NOT_FOUND", "Assessment has not been submitted yet.")
        evaluation = self.db.scalar(select(EvaluationEntity).where(EvaluationEntity.submission_id == submission.id).limit(1))
        if evaluation is None:
            raise AppError(404, "EVALUATION_NOT_FOUND", "Evaluation has not been generated yet.")
        return Evaluation.model_validate(evaluation)

    def get_current_workflow(self) -> WorkflowState:
        workflow = self.db.scalar(select(WorkflowStateEntity).limit(1))
        if workflow is None:
            workflow = self._ensure_workflow()
            self.db.commit()
        return WorkflowState.model_validate(workflow)

    def advance_workflow(self, next_stage: WorkflowStage, reason: str) -> WorkflowState:
        workflow = self._ensure_workflow()
        current_stage = WorkflowStage(workflow.current_stage)
        if not can_transition(current_stage, next_stage):
            raise AppError(
                409,
                "INVALID_WORKFLOW_TRANSITION",
                "Requested workflow transition is not allowed.",
                {"current_stage": current_stage.value, "next_stage": next_stage.value},
            )
        self._transition_workflow(workflow, next_stage, reason)
        self.db.commit()
        self.db.refresh(workflow)
        return WorkflowState.model_validate(workflow)

    def proceed_workflow(self) -> WorkflowState:
        workflow = self._ensure_workflow()
        current_stage = WorkflowStage(workflow.current_stage)
        if current_stage == WorkflowStage.UNIT_REVIEW:
            workflow.recent_assessment_id = None
            self._transition_workflow(workflow, WorkflowStage.UNIT_TEST, "Unit review completed. Generate a unit assessment.")
        elif current_stage == WorkflowStage.FINAL_REVIEW:
            workflow.recent_assessment_id = None
            self._transition_workflow(workflow, WorkflowStage.FINAL_TEST, "Final review completed. Generate a final assessment.")
        else:
            raise AppError(
                409,
                "INVALID_WORKFLOW_PROCEED",
                "The current workflow stage does not support proceed.",
                {"current_stage": current_stage.value},
            )
        self.db.commit()
        self.db.refresh(workflow)
        return WorkflowState.model_validate(workflow)

    def _apply_assessment_outcome(
        self,
        workflow: WorkflowStateEntity,
        assessment: AssessmentEntity,
        outcome: ScoringOutcome,
        evaluation_model: Evaluation,
    ) -> tuple[WorkflowStage, str]:
        assessment_type = AssessmentType(assessment.type)
        passed = outcome.passed
        current_micro_plan = self.db.get(MicroPlanEntity, assessment.linked_plan_id)
        if current_micro_plan is None or current_micro_plan.deleted_at is not None:
            raise AppError(404, "MICRO_PLAN_NOT_FOUND", "Micro plan does not exist.")

        if not passed:
            self._apply_micro_plan_adjustment(
                current_micro_plan,
                adjustment_mode="remediation",
                assessment_type=assessment_type,
                evaluation=evaluation_model,
            )
            return WorkflowStage.LEARNING, self._assessment_failure_reason(assessment_type)

        macro_plan = self.db.get(MacroPlanEntity, current_micro_plan.macro_plan_id)
        current_micro_plan.status = PlanStatus.COMPLETED.value
        current_micro_plan.updated_at = utcnow()

        if assessment_type == AssessmentType.CHECKPOINT:
            next_unit = self._find_next_unit(macro_plan, current_micro_plan.unit_id) if macro_plan else None
            if next_unit is None:
                if macro_plan is not None:
                    macro_plan.status = PlanStatus.COMPLETED.value
                    macro_plan.updated_at = utcnow()
                return WorkflowStage.NEXT_CYCLE, "Checkpoint cleared. Current cycle completed."
            next_micro_plan = self._create_next_micro_plan(
                macro_plan,
                current_micro_plan,
                next_unit,
                evaluation_model,
                assessment_type=assessment_type,
            )
            workflow.current_micro_plan_id = next_micro_plan.id
            return WorkflowStage.LEARNING, f"Checkpoint cleared. Continue with {next_micro_plan.title}."

        if assessment_type == AssessmentType.UNIT:
            next_unit = self._find_next_unit(macro_plan, current_micro_plan.unit_id) if macro_plan else None
            if next_unit is None:
                return WorkflowStage.FINAL_REVIEW, "Unit test cleared. Prepare for final review."
            next_micro_plan = self._create_next_micro_plan(
                macro_plan,
                current_micro_plan,
                next_unit,
                evaluation_model,
                assessment_type=assessment_type,
            )
            workflow.current_micro_plan_id = next_micro_plan.id
            return WorkflowStage.LEARNING, f"Unit cleared. Continue with {next_micro_plan.title}."

        if macro_plan is not None:
            macro_plan.status = PlanStatus.COMPLETED.value
            macro_plan.updated_at = utcnow()
        return WorkflowStage.NEXT_CYCLE, "Final test cleared. Current cycle completed."

    def _create_next_micro_plan(
        self,
        macro_plan: MacroPlanEntity,
        current_micro_plan: MicroPlanEntity,
        target_unit: dict[str, Any],
        evaluation_model: Evaluation,
        *,
        assessment_type: AssessmentType,
    ) -> MicroPlanEntity:
        adjustment = self._run_graph(
            "plan_agent",
            "adjust_micro_plan",
            WorkflowStage.LEARNING,
            {
                "adjustment_mode": "next_unit",
                "assessment_type": assessment_type.value,
                "current_micro_plan": self._micro_plan_context(current_micro_plan),
                "target_unit": target_unit,
                "evaluation": evaluation_model.model_dump(mode="json"),
                "time_budget": macro_plan.duration,
            },
        )
        next_payload = adjustment.payload["micro_plan"]
        now = utcnow()
        next_micro_plan = MicroPlanEntity(
            id=str(uuid4()),
            macro_plan_id=macro_plan.id,
            unit_id=str(target_unit.get("id") or next_payload.get("unit_id") or current_micro_plan.unit_id),
            title=next_payload["title"],
            topics=next_payload["topics"],
            estimated_duration=self._coerce_estimated_duration(next_payload.get("estimated_duration"), current_micro_plan.estimated_duration),
            tasks=next_payload["tasks"],
            completion_criteria=next_payload["completion_criteria"],
            assessment_trigger=next_payload["assessment_trigger"],
            status=PlanStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        self.db.add(next_micro_plan)
        self.db.flush()
        return next_micro_plan

    def _apply_micro_plan_adjustment(
        self,
        micro_plan: MicroPlanEntity,
        *,
        adjustment_mode: str,
        assessment_type: AssessmentType,
        evaluation: Evaluation,
    ) -> None:
        adjustment = self._run_graph(
            "plan_agent",
            "adjust_micro_plan",
            WorkflowStage.LEARNING,
            {
                "adjustment_mode": adjustment_mode,
                "assessment_type": assessment_type.value,
                "current_micro_plan": self._micro_plan_context(micro_plan),
                "evaluation": evaluation.model_dump(mode="json"),
                "time_budget": {"value": micro_plan.estimated_duration, "unit": "minute"},
            },
        )
        adjusted_payload = adjustment.payload["micro_plan"]
        micro_plan.title = adjusted_payload["title"]
        micro_plan.topics = adjusted_payload["topics"]
        micro_plan.estimated_duration = self._coerce_estimated_duration(adjusted_payload.get("estimated_duration"), micro_plan.estimated_duration)
        micro_plan.tasks = adjusted_payload["tasks"]
        micro_plan.completion_criteria = adjusted_payload["completion_criteria"]
        micro_plan.assessment_trigger = adjusted_payload["assessment_trigger"]
        micro_plan.updated_at = utcnow()

    def _get_visible_macro_plan(self, plan_id: str | None) -> MacroPlanEntity | None:
        if not plan_id:
            return None
        macro_plan = self.db.get(MacroPlanEntity, plan_id)
        if macro_plan is None or macro_plan.deleted_at is not None:
            return None
        return macro_plan

    def _get_visible_micro_plan(self, micro_plan_id: str | None) -> MicroPlanEntity | None:
        if not micro_plan_id:
            return None
        micro_plan = self.db.get(MicroPlanEntity, micro_plan_id)
        if micro_plan is None or micro_plan.deleted_at is not None:
            return None
        return micro_plan

    def _latest_visible_macro_plan(self, *, exclude_plan_id: str | None = None) -> MacroPlanEntity | None:
        stmt = select(MacroPlanEntity).where(MacroPlanEntity.deleted_at.is_(None)).order_by(desc(MacroPlanEntity.updated_at))
        macros = list(self.db.scalars(stmt).all())
        for macro_plan in macros:
            if exclude_plan_id and macro_plan.id == exclude_plan_id:
                continue
            return macro_plan
        return None

    def _resolve_display_micro_plan(self, plan_id: str) -> MicroPlanEntity | None:
        micro_plans = list(
            self.db.scalars(
                select(MicroPlanEntity)
                .where(MicroPlanEntity.macro_plan_id == plan_id)
                .where(MicroPlanEntity.deleted_at.is_(None))
                .order_by(desc(MicroPlanEntity.created_at))
            ).all()
        )
        if not micro_plans:
            return None

        active_micro_plan = next((micro_plan for micro_plan in micro_plans if micro_plan.status == PlanStatus.ACTIVE.value), None)
        return active_micro_plan or micro_plans[0]

    def _build_plan_card_summary(
        self,
        macro_plan: MacroPlanEntity,
        micro_plans: list[MicroPlanEntity],
        workflow: WorkflowStateEntity | None,
    ) -> PlanCardSummary:
        current_micro_plan = next(
            (micro_plan for micro_plan in micro_plans if workflow and micro_plan.id == workflow.current_micro_plan_id),
            None,
        )
        fallback_micro_plan = next(
            (micro_plan for micro_plan in micro_plans if micro_plan.status == PlanStatus.ACTIVE.value),
            micro_plans[0] if micro_plans else None,
        )
        display_micro_plan = current_micro_plan or fallback_micro_plan
        unit_count = len(macro_plan.units or [])
        completed_unit_count = sum(1 for micro_plan in micro_plans if micro_plan.status == PlanStatus.COMPLETED.value)

        if macro_plan.status == PlanStatus.COMPLETED.value:
            progress_percent = 100
        elif unit_count > 0:
            progress_percent = max(0, min(100, round((completed_unit_count / unit_count) * 100)))
        else:
            progress_percent = 0

        return PlanCardSummary(
            id=macro_plan.id,
            title=macro_plan.title,
            goal=macro_plan.goal,
            status=PlanStatus(macro_plan.status),
            version=macro_plan.version,
            created_at=macro_plan.created_at,
            updated_at=macro_plan.updated_at,
            unit_count=unit_count,
            completed_unit_count=completed_unit_count,
            progress_percent=progress_percent,
            current_micro_plan_id=display_micro_plan.id if display_micro_plan else None,
            current_micro_plan_title=display_micro_plan.title if display_micro_plan else None,
            is_current=bool(workflow and workflow.current_macro_plan_id == macro_plan.id),
        )

    def _micro_plan_sort_key(self, macro_plan: MacroPlanEntity, micro_plan: MicroPlanEntity) -> tuple[int, float]:
        unit_order = {
            str(unit.get("id")): index
            for index, unit in enumerate(macro_plan.units or [])
            if isinstance(unit, dict)
        }
        return (unit_order.get(micro_plan.unit_id, len(unit_order) + 1), micro_plan.created_at.timestamp())

    def _build_plan_generation_request_from_assistant(
        self,
        session: PlanAssistantSessionEntity,
        profile: UserProfileEntity,
        ready_assets: list[Any],
    ) -> PlanGenerateRequest:
        user_messages = [
            str(turn.get("message", "")).strip()
            for turn in session.conversation_turns
            if str(turn.get("role")) == "user" and str(turn.get("message", "")).strip()
        ]
        conversation_text = "\n".join(user_messages)
        learning_goals = session.conversation_summary if session.conversation_summary and user_messages else profile.learning_goals

        return PlanGenerateRequest(
            learning_goals=learning_goals,
            time_budget=self._infer_time_budget(conversation_text, profile.time_budget),
            current_level=self._infer_current_level(conversation_text, profile.current_level),
            preferred_style=self._infer_preferred_style(conversation_text, profile.preferred_style),
            preferred_difficulty=self._infer_preferred_difficulty(conversation_text, profile.preferred_difficulty),
            preferred_question_types=self._infer_preferred_question_types(conversation_text, profile.preferred_question_types),
            attached_asset_ids=[asset.id for asset in ready_assets],
        )

    def _infer_time_budget(self, conversation_text: str, fallback: dict[str, Any]) -> dict[str, str | int]:
        text = conversation_text.lower()
        patterns = [
            (r"(\d+)\s*(?:day|days|天)", "day", 1),
            (r"(\d+)\s*(?:week|weeks|周)", "week", 1),
            (r"(\d+)\s*(?:month|months|个月|月)", "week", 4),
            (r"(\d+)\s*(?:session|sessions|次课|节课)", "session", 1),
        ]
        for pattern, unit, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                return {"value": max(1, int(match.group(1)) * multiplier), "unit": unit}
        return {"value": int(fallback.get("value", 45)), "unit": str(fallback.get("unit", "day"))}

    def _infer_current_level(self, conversation_text: str, fallback: str) -> str:
        text = conversation_text.lower()
        if any(keyword in text for keyword in ["零基础", "新手", "beginner", "starter", "入门"]):
            return "beginner"
        if any(keyword in text for keyword in ["intermediate", "有基础", "中级", "进阶"]):
            return "intermediate"
        if any(keyword in text for keyword in ["advanced", "熟练", "高级", "expert"]):
            return "advanced"
        return fallback

    def _infer_preferred_style(self, conversation_text: str, fallback: str) -> str:
        text = conversation_text.lower()
        if any(keyword in text for keyword in ["实战", "practical", "practice", "动手", "案例"]):
            return "practical"
        if any(keyword in text for keyword in ["rigorous", "系统", "严谨", "推导"]):
            return "rigorous"
        if any(keyword in text for keyword in ["visual", "图示", "可视化", "图解"]):
            return "visual"
        return fallback

    def _infer_preferred_difficulty(self, conversation_text: str, fallback: str) -> str:
        text = conversation_text.lower()
        if any(keyword in text for keyword in ["easy", "简单", "轻松", "基础版"]):
            return "easy"
        if any(keyword in text for keyword in ["hard", "困难", "高强度", "challenging"]):
            return "hard"
        if any(keyword in text for keyword in ["medium", "中等", "适中"]):
            return "medium"
        return fallback

    def _infer_preferred_question_types(self, conversation_text: str, fallback: list[str]) -> list[str]:
        text = conversation_text.lower()
        inferred: list[str] = []
        if any(keyword in text for keyword in ["single choice", "单选", "选择题"]):
            inferred.append("single_choice")
        if any(keyword in text for keyword in ["multiple choice", "多选"]):
            inferred.append("multiple_choice")
        if any(keyword in text for keyword in ["short answer", "简答", "问答"]):
            inferred.append("short_answer")
        return inferred or fallback or ["single_choice"]

    def _validate_assessment_type_for_stage(self, assessment_type: AssessmentType, current_stage: WorkflowStage) -> None:
        expected_stage = ASSESSMENT_STAGE_BY_TYPE[assessment_type]
        if current_stage != expected_stage:
            raise AppError(
                409,
                "ASSESSMENT_TYPE_STAGE_MISMATCH",
                "The requested assessment type does not match the current workflow stage.",
                {"current_stage": current_stage.value, "assessment_type": assessment_type.value},
            )

    def _assessment_generation_reason(self, assessment_type: AssessmentType) -> str:
        if assessment_type == AssessmentType.CHECKPOINT:
            return "Stage assessment generated. Pass it to unlock the next micro study session."
        if assessment_type == AssessmentType.UNIT:
            return "Unit assessment generated. Submit answers to continue."
        return "Final assessment generated. Submit answers to continue."

    def _assessment_failure_reason(self, assessment_type: AssessmentType) -> str:
        if assessment_type == AssessmentType.CHECKPOINT:
            return "Stage assessment not cleared. Continue the current micro study session."
        if assessment_type == AssessmentType.UNIT:
            return "Unit test requires more study."
        return "Final test requires targeted remediation."

    def _find_next_unit(self, macro_plan: MacroPlanEntity | None, current_unit_id: str) -> dict[str, Any] | None:
        if macro_plan is None:
            return None
        units = macro_plan.units or []
        for index, unit in enumerate(units):
            if not isinstance(unit, dict):
                continue
            if str(unit.get("id")) == current_unit_id:
                for next_unit in units[index + 1 :]:
                    if isinstance(next_unit, dict):
                        return next_unit
                return None
        return units[0] if units and isinstance(units[0], dict) else None

    def _micro_plan_context(self, micro_plan: MicroPlanEntity) -> dict[str, Any]:
        return {
            "id": micro_plan.id,
            "unit_id": micro_plan.unit_id,
            "title": micro_plan.title,
            "topics": micro_plan.topics,
            "estimated_duration": micro_plan.estimated_duration,
            "tasks": micro_plan.tasks,
            "completion_criteria": micro_plan.completion_criteria,
            "assessment_trigger": micro_plan.assessment_trigger,
        }

    @staticmethod
    def _coerce_estimated_duration(value: Any, fallback: Any) -> int:
        try:
            return max(1, int(round(float(value))))
        except (TypeError, ValueError):
            return max(1, int(round(float(fallback or 45))))

    def _ensure_workflow(self) -> WorkflowStateEntity:
        workflow = self.db.scalar(select(WorkflowStateEntity).limit(1))
        if workflow is not None:
            return workflow
        workflow = WorkflowStateEntity(
            id=str(uuid4()),
            current_stage=WorkflowStage.ONBOARDING.value,
            current_macro_plan_id=None,
            current_micro_plan_id=None,
            recent_assessment_id=None,
            next_action="Create your learner profile to unlock planning.",
            stage_history=[],
            updated_at=utcnow(),
        )
        self.db.add(workflow)
        self.db.flush()
        return workflow

    def _transition_workflow(
        self,
        workflow: WorkflowStateEntity,
        next_stage: WorkflowStage,
        reason: str,
        *,
        validate: bool = True,
    ) -> None:
        previous_stage = WorkflowStage(workflow.current_stage)
        if validate and previous_stage != next_stage and not can_transition(previous_stage, next_stage):
            raise AppError(
                409,
                "INVALID_WORKFLOW_TRANSITION",
                "Requested workflow transition is not allowed.",
                {"current_stage": previous_stage.value, "next_stage": next_stage.value},
            )
        workflow.current_stage = next_stage.value
        workflow.next_action = reason
        workflow.stage_history = [*workflow.stage_history, {"from": previous_stage.value, "to": next_stage.value, "reason": reason}]
        workflow.updated_at = utcnow()

    def _run_graph(self, target_agent: str, task_type: str, next_stage: WorkflowStage, input_context: dict[str, Any]) -> OrchestrationResult:
        task = self._log_task(target_agent, task_type, input_context, task_type)
        initial_state = {"target_agent": target_agent, "task_type": task_type, "input_context": input_context}
        if StateGraph is not None:
            graph = StateGraph(dict)
            graph.add_node("supervisor", self._supervisor_node)
            graph.add_node(target_agent, self._agent_node)
            graph.add_edge(START, "supervisor")
            graph.add_edge("supervisor", target_agent)
            graph.add_edge(target_agent, END)
            output = graph.compile().invoke(initial_state)
        else:
            output = self._agent_node(self._supervisor_node(initial_state))
        self._log_decision(task.id, output["summary"], next_stage, output["payload"])
        return OrchestrationResult(payload=output["payload"], next_stage=next_stage, summary=output["summary"])

    def _supervisor_node(self, state: dict[str, Any]) -> dict[str, Any]:
        return {**state, "supervisor_reason": f"Route {state['task_type']} to {state['target_agent']} based on the workflow state."}

    def _agent_node(self, state: dict[str, Any]) -> dict[str, Any]:
        task_type = state["task_type"]
        if task_type == "generate_plan":
            payload = self.llm_provider.generate_structured("plan_generation", state["input_context"])
            summary = f"Generated macro/micro plan for {state['input_context']['learning_goals']}."
        elif task_type == "adjust_micro_plan":
            payload = self.llm_provider.generate_structured("plan_adjustment", state["input_context"])
            summary = payload.get("adjustment_summary") or f"Adjusted micro plan for {state['input_context']['adjustment_mode']}."
        elif task_type == "learning_message":
            payload = self.llm_provider.generate_structured("learning_reply", state["input_context"])
            summary = f"Answered learner question for session {state['input_context']['session_id']}."
        elif task_type == "generate_assessment":
            payload = self.llm_provider.generate_structured("assessment_generation", state["input_context"])
            summary = (
                f"Generated {state['input_context']['assessment_type']} assessment for micro plan "
                f"{state['input_context']['linked_plan_id']}."
            )
        else:
            raise AppError(500, "UNKNOWN_TASK_TYPE", f"Unsupported workflow task type: {task_type}")
        return {**state, "payload": payload, "summary": summary}

    def _log_task(self, target_agent: str, task_type: str, input_context: dict[str, Any], trigger_reason: str) -> AgentTaskEntity:
        task = AgentTaskEntity(
            id=str(uuid4()),
            target_agent=target_agent,
            task_type=task_type,
            input_context=input_context,
            trigger_reason=trigger_reason,
            created_at=utcnow(),
        )
        self.db.add(task)
        self.db.flush()
        return task

    def _log_decision(self, task_id: str, summary: str, next_state: WorkflowStage, payload: dict[str, Any]) -> None:
        decision = AgentDecisionEntity(
            id=str(uuid4()),
            task_id=task_id,
            decision_summary=summary,
            next_state=next_state.value,
            artifacts=payload,
            created_at=utcnow(),
        )
        self.db.add(decision)
        self.db.flush()
