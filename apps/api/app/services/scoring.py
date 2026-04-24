from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import uuid4

from app.schemas.assessment import Evaluation, QuestionResult, RubricResult, SubmissionAnswer
from app.services.llm_provider import LLMProviderAdapter
from app.services.utils import utcnow


@dataclass(slots=True)
class ScoringOutcome:
    score: float
    earned_points: float
    total_points: float
    score_ratio: float
    passed: bool
    feedback: str
    mistake_analysis: list[dict]
    recommendations: list[str]
    question_results: list[QuestionResult]


class ScoringService:
    def __init__(self, llm_provider: LLMProviderAdapter) -> None:
        self.llm_provider = llm_provider

    def evaluate(
        self,
        questions: list[dict],
        answers: list[SubmissionAnswer],
        uncertainties: list[str],
        *,
        assessment_type: str = "checkpoint",
        mastery_threshold: float = 0.8,
    ) -> ScoringOutcome:
        answer_map = {item.question_id: item.answer for item in answers}
        uncertain_ids = set(uncertainties)
        total_points = max(
            1.0,
            sum(
                float(
                    question.get(
                        "points",
                        2 if question.get("question_type") in {"single_choice", "multiple_choice", "true_false"} else 5,
                    )
                )
                for question in questions
            ),
        )
        earned_points = 0.0
        mistakes: list[dict] = []
        question_results: list[QuestionResult] = []

        for question in questions:
            question_id = question["id"]
            submitted = answer_map.get(question_id, "")
            is_objective = question["question_type"] in {"single_choice", "multiple_choice", "true_false"}
            max_points = float(question.get("points", 2 if is_objective else 5))
            rubric = question.get("rubric") or self._build_default_rubric(question, max_points)
            if is_objective:
                expected = question.get("correct_answer", "")
                explanation = str(question.get("explanation") or "Review the concept tested by this option and try again.")
                if question_id in uncertain_ids:
                    mistakes.append(
                        {
                            "question_id": question_id,
                            "area": question.get("expected_competency", "objective recall"),
                            "impact": "medium",
                            "reason": "Question marked as uncertain.",
                        }
                    )
                    question_results.append(
                        QuestionResult(
                            question_id=question_id,
                            question_type=question["question_type"],
                            submitted_answer="",
                            earned_points=0.0,
                            max_points=max_points,
                            is_correct=False,
                            correct_answer=str(expected),
                            explanation=explanation,
                            error_reason="This question was marked as uncertain, so it received 0 points.",
                        )
                    )
                elif not submitted.strip():
                    mistakes.append(
                        {
                            "question_id": question_id,
                            "area": question.get("expected_competency", "objective recall"),
                            "impact": "medium",
                            "reason": "No answer submitted.",
                        }
                    )
                    question_results.append(
                        QuestionResult(
                            question_id=question_id,
                            question_type=question["question_type"],
                            submitted_answer="",
                            earned_points=0.0,
                            max_points=max_points,
                            is_correct=False,
                            correct_answer=str(expected),
                            explanation=explanation,
                            error_reason="No answer was submitted for this question.",
                        )
                    )
                elif submitted.strip().lower() == str(expected).strip().lower():
                    earned_points += max_points
                    question_results.append(
                        QuestionResult(
                            question_id=question_id,
                            question_type=question["question_type"],
                            submitted_answer=submitted.strip(),
                            earned_points=max_points,
                            max_points=max_points,
                            is_correct=True,
                            correct_answer=str(expected),
                            explanation=explanation,
                        )
                    )
                else:
                    mistakes.append(
                        {
                            "question_id": question_id,
                            "area": question.get("expected_competency", "objective recall"),
                            "impact": "medium",
                            "reason": "Selected the wrong option.",
                        }
                    )
                    question_results.append(
                        QuestionResult(
                            question_id=question_id,
                            question_type=question["question_type"],
                            submitted_answer=submitted.strip(),
                            earned_points=0.0,
                            max_points=max_points,
                            is_correct=False,
                            correct_answer=str(expected),
                            explanation=explanation,
                            error_reason="The selected option does not match the correct answer.",
                        )
                    )
            else:
                if question_id in uncertain_ids:
                    rubric_results = [
                        RubricResult(
                            criterion=str(item.get("criterion", "")),
                            earned_points=0.0,
                            max_points=float(item.get("points", 0)),
                            feedback="This criterion was not met because the answer was marked as uncertain.",
                        )
                        for item in rubric
                    ]
                    mistakes.append(
                        {
                            "question_id": question_id,
                            "area": question.get("expected_competency", "explanation quality"),
                            "impact": "high",
                            "reason": "Question marked as uncertain.",
                        }
                    )
                    question_results.append(
                        QuestionResult(
                            question_id=question_id,
                            question_type=question["question_type"],
                            submitted_answer="",
                            earned_points=0.0,
                            max_points=max_points,
                            explanation="Follow the rubric criteria and answer each requested part explicitly.",
                            error_reason="This question was marked as uncertain, so it received 0 points.",
                            rubric_results=rubric_results,
                        )
                    )
                    continue

                if not submitted.strip():
                    rubric_results = [
                        RubricResult(
                            criterion=str(item.get("criterion", "")),
                            earned_points=0.0,
                            max_points=float(item.get("points", 0)),
                            feedback="No evidence was provided for this rubric item.",
                        )
                        for item in rubric
                    ]
                    mistakes.append(
                        {
                            "question_id": question_id,
                            "area": question.get("expected_competency", "explanation quality"),
                            "impact": "high",
                            "reason": "No answer submitted.",
                        }
                    )
                    question_results.append(
                        QuestionResult(
                            question_id=question_id,
                            question_type=question["question_type"],
                            submitted_answer="",
                            earned_points=0.0,
                            max_points=max_points,
                            explanation="Follow the rubric criteria and answer each requested part explicitly.",
                            error_reason="No answer was submitted for this question.",
                            rubric_results=rubric_results,
                        )
                    )
                    continue

                result = self.llm_provider.generate_structured(
                    "subjective_evaluation",
                    {
                        "answer": submitted,
                        "rubric": rubric,
                    },
                )
                rubric_results = [
                    RubricResult(
                        criterion=str(item.get("criterion", "")),
                        earned_points=float(item.get("earned_points", 0)),
                        max_points=float(item.get("max_points", 0)),
                        feedback=str(item.get("feedback", "")).strip(),
                    )
                    for item in result.get("rubric_results", [])
                ]
                subjective_points = round(sum(item.earned_points for item in rubric_results), 2)
                earned_points += subjective_points
                overall_feedback = str(
                    result.get("overall_feedback") or "Follow the rubric criteria and address the missed points."
                ).strip()
                error_reason = None if subjective_points >= max_points else "Some rubric criteria were only partially satisfied."
                if subjective_points < max_points:
                    mistakes.append(
                        {
                            "question_id": question_id,
                            "area": question.get("expected_competency", "explanation quality"),
                            "impact": "high",
                            "reason": error_reason,
                        }
                    )
                question_results.append(
                    QuestionResult(
                        question_id=question_id,
                        question_type=question["question_type"],
                        submitted_answer=submitted.strip(),
                        earned_points=subjective_points,
                        max_points=max_points,
                        explanation=overall_feedback,
                        error_reason=error_reason,
                        rubric_results=rubric_results,
                    )
                )

        score_ratio = round(earned_points / total_points, 2)
        passed = score_ratio >= mastery_threshold
        recommendations = self._build_recommendations(mistakes, uncertainties, assessment_type=assessment_type, passed=passed)
        feedback = (
            "You demonstrated stable understanding of the current study scope."
            if passed
            else "You should reinforce the active topic before moving on."
        )
        return ScoringOutcome(
            score=score_ratio,
            earned_points=round(earned_points, 2),
            total_points=round(total_points, 2),
            score_ratio=score_ratio,
            passed=passed,
            feedback=feedback,
            mistake_analysis=mistakes,
            recommendations=recommendations,
            question_results=question_results,
        )

    @staticmethod
    def _build_recommendations(
        mistakes: Iterable[dict],
        uncertainties: list[str],
        *,
        assessment_type: str,
        passed: bool,
    ) -> list[str]:
        recommendations = []
        assessment_label = assessment_type.replace("_", " ")
        if list(mistakes):
            recommendations.append(f"Review the weak competencies flagged in the latest {assessment_label} assessment.")
        if uncertainties:
            recommendations.append("Revisit the questions marked as uncertain and summarize the concept again.")
        if passed:
            recommendations.append("Proceed to the next micro study session and carry forward the corrected ideas.")
        if not recommendations:
            recommendations.append("Proceed to the next study phase and keep your notes for quick review.")
        return recommendations

    def build_evaluation(self, submission_id: str, outcome: ScoringOutcome) -> Evaluation:
        return Evaluation(
            id=str(uuid4()),
            submission_id=submission_id,
            score=outcome.score,
            earned_points=outcome.earned_points,
            total_points=outcome.total_points,
            score_ratio=outcome.score_ratio,
            passed=outcome.passed,
            feedback=outcome.feedback,
            mistake_analysis=outcome.mistake_analysis,
            recommendations=outcome.recommendations,
            question_results=outcome.question_results,
            created_at=utcnow(),
        )

    @staticmethod
    def _build_default_rubric(question: dict, max_points: float) -> list[dict]:
        keywords = [str(item).strip() for item in question.get("rubric_keywords", []) if str(item).strip()]
        if not keywords:
            return []
        return [
            {
                "criterion": "Address the expected concept",
                "points": max_points,
                "keywords": keywords,
                "description": "Reference the expected concept directly in the answer.",
            }
        ]
