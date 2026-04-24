from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import StudyPilotModel
from app.schemas.enums import AssessmentStatus, AssessmentType


class RubricCriterion(StudyPilotModel):
    criterion: str
    points: float
    keywords: list[str] = Field(default_factory=list)
    description: str = ""


class RubricResult(StudyPilotModel):
    criterion: str
    earned_points: float
    max_points: float
    feedback: str


class QuestionResult(StudyPilotModel):
    question_id: str
    question_type: str
    submitted_answer: str
    earned_points: float
    max_points: float
    is_correct: bool | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    error_reason: str | None = None
    rubric_results: list[RubricResult] = Field(default_factory=list)


class Question(StudyPilotModel):
    id: str
    assessment_id: str
    question_type: str
    stem: str
    options: list[str] = Field(default_factory=list)
    reference_scope: str
    expected_competency: str
    points: float
    explanation: str | None = None
    rubric: list[RubricCriterion] = Field(default_factory=list)


class Assessment(StudyPilotModel):
    id: str
    type: AssessmentType
    scope: str
    linked_plan_id: str
    questions: list[Question] = Field(default_factory=list)
    difficulty: str
    status: AssessmentStatus
    created_at: datetime
    updated_at: datetime


class SubmissionAnswer(StudyPilotModel):
    question_id: str
    answer: str


class Submission(StudyPilotModel):
    id: str
    assessment_id: str
    answers: list[SubmissionAnswer] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    submitted_at: datetime


class Evaluation(StudyPilotModel):
    id: str
    submission_id: str
    score: float
    earned_points: float
    total_points: float
    score_ratio: float
    passed: bool
    feedback: str
    mistake_analysis: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    question_results: list[QuestionResult] = Field(default_factory=list)
    created_at: datetime


class AssessmentGenerateRequest(StudyPilotModel):
    linked_plan_id: str
    type: AssessmentType = AssessmentType.CHECKPOINT


class AssessmentSubmitRequest(StudyPilotModel):
    answers: list[SubmissionAnswer] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class AssessmentSubmitResponse(StudyPilotModel):
    submission: Submission
    evaluation: Evaluation
