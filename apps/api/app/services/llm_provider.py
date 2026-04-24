from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings
from app.core.errors import AppError

SINGLE_CHOICE_QUESTION_COUNT = 10
SHORT_ANSWER_QUESTION_COUNT = 2
SINGLE_CHOICE_POINTS = 2.0
SHORT_ANSWER_POINTS = 5.0


class LLMProviderAdapter(Protocol):
    def generate_structured(self, task_name: str, context: dict[str, Any]) -> dict[str, Any]:
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


@dataclass(slots=True)
class OpenAICompatibleProvider:
    base_url: str | None
    api_key: str
    model: str
    embedding_model: str
    allow_fake_embedding_fallback: bool = False

    def _build_client(self) -> Any:
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise AppError(503, "LLM_DEPENDENCY_MISSING", "OpenAI client dependency is not installed.") from exc
        return OpenAI(base_url=self.base_url, api_key=self.api_key)

    def generate_structured(self, task_name: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Return strict JSON only.\n"
            f"task={task_name}\n"
            f"schema={self._task_schema(task_name)}\n"
            f"context={json.dumps(context, ensure_ascii=True)}"
        )
        try:
            client = self._build_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a structured StudyPilot backend component. "
                            "Return one JSON object only, with exactly the required keys for the requested task. "
                            "Do not use markdown fences, commentary, or extra keys."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            payload = json.loads(self._extract_json(content))
            return self._normalize_payload(task_name, payload, context)
        except AppError:
            raise
        except TimeoutError as exc:
            raise AppError(504, "LLM_TIMEOUT", "The upstream LLM request timed out.") from exc
        except Exception as exc:
            raise AppError(502, "LLM_UPSTREAM_ERROR", "The upstream LLM request failed.") from exc

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            client = self._build_client()
            response = client.embeddings.create(model=self.embedding_model, input=texts)
            return [list(item.embedding) for item in response.data]
        except AppError:
            raise
        except TimeoutError as exc:
            raise AppError(504, "EMBEDDING_TIMEOUT", "The embedding request timed out.") from exc
        except Exception as exc:
            if self.allow_fake_embedding_fallback:
                return FakeLLMProvider().embed_texts(texts)
            raise AppError(502, "EMBEDDING_UPSTREAM_ERROR", "The embedding request failed.") from exc

    @staticmethod
    def _extract_json(content: str) -> str:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise AppError(502, "INVALID_LLM_RESPONSE", "The LLM response was not valid JSON.")
        return match.group(0)

    @staticmethod
    def _task_schema(task_name: str) -> str:
        if task_name == "plan_generation":
            return json.dumps(
                {
                    "macro_plan": {
                        "title": "string",
                        "goal": "string",
                        "duration": {"value": "number", "unit": "string"},
                        "milestones": [{"title": "string", "target": "string"}],
                        "units": [{"id": "string", "title": "string", "objective": "string"}],
                    },
                    "micro_plan": {
                        "unit_id": "string",
                        "title": "string",
                        "topics": ["string"],
                        "estimated_duration": "number",
                        "tasks": [{"title": "string", "status": "pending"}],
                        "completion_criteria": ["string"],
                        "assessment_trigger": {"type": "string", "minimum_tasks": "number"},
                    },
                },
                ensure_ascii=True,
            )
        if task_name == "plan_adjustment":
            return json.dumps(
                {
                    "micro_plan": {
                        "unit_id": "string",
                        "title": "string",
                        "topics": ["string"],
                        "estimated_duration": "number",
                        "tasks": [{"title": "string", "status": "pending"}],
                        "completion_criteria": ["string"],
                        "assessment_trigger": {"type": "string", "minimum_tasks": "number"},
                    },
                    "adjustment_summary": "string",
                },
                ensure_ascii=True,
            )
        if task_name == "learning_reply":
            return json.dumps(
                {
                    "reply": "string",
                    "session_summary": "string",
                    "mastery_signals": ["string"],
                },
                ensure_ascii=True,
            )
        if task_name == "plan_assistant_reply":
            return json.dumps(
                {
                    "reply": "string",
                    "conversation_summary": "string",
                },
                ensure_ascii=True,
            )
        if task_name == "assessment_generation":
            return json.dumps(
                {
                    "scope": "string",
                    "difficulty": "string",
                    "questions": [
                        {
                            "question_type": "single_choice|short_answer",
                            "stem": "string",
                            "options": ["string"],
                            "reference_scope": "string",
                            "expected_competency": "string",
                            "points": "number",
                            "correct_answer": "string",
                            "explanation": "string",
                            "rubric": [
                                {
                                    "criterion": "string",
                                    "points": "number",
                                    "keywords": ["string"],
                                    "description": "string",
                                }
                            ],
                        }
                    ],
                },
                ensure_ascii=True,
            )
        if task_name == "subjective_evaluation":
            return json.dumps(
                {
                    "rubric_results": [
                        {
                            "criterion": "string",
                            "earned_points": "number",
                            "feedback": "string",
                        }
                    ],
                    "overall_feedback": "string",
                },
                ensure_ascii=True,
            )
        raise AppError(500, "UNKNOWN_LLM_TASK", f"Unsupported LLM task: {task_name}")

    @staticmethod
    def _normalize_payload(task_name: str, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if task_name == "plan_generation":
            default_unit_id = "unit-1"
            macro_plan = payload.get("macro_plan", {})
            units = macro_plan.get("units")
            normalized_units = []
            if isinstance(units, list):
                for index, unit in enumerate(units, start=1):
                    if not isinstance(unit, dict):
                        continue
                    normalized_units.append(
                        {
                            "id": str(unit.get("id") or f"unit-{index}"),
                            "title": str(unit.get("title") or f"Study Unit {index}").strip(),
                            "objective": str(unit.get("objective") or context["learning_goals"]).strip(),
                        }
                    )
            if not normalized_units:
                normalized_units = [
                    {
                        "id": default_unit_id,
                        "title": "Focused Study Unit",
                        "objective": context["learning_goals"],
                    }
                ]

            return {
                "macro_plan": {
                    "title": str(macro_plan.get("title") or f"{context['learning_goals']} Learning Plan").strip(),
                    "goal": str(macro_plan.get("goal") or context["learning_goals"]).strip(),
                    "duration": macro_plan.get("duration") or context["time_budget"],
                    "milestones": macro_plan.get("milestones")
                    if isinstance(macro_plan.get("milestones"), list)
                    else [
                        {"title": "Build foundations", "target": f"Understand the scope of {context['learning_goals']}"},
                        {"title": "Finish guided practice", "target": "Complete the current study cycle"},
                    ],
                    "units": normalized_units,
                },
                "micro_plan": OpenAICompatibleProvider._normalize_micro_plan_payload(
                    payload.get("micro_plan", {}),
                    fallback_unit_id=normalized_units[0]["id"],
                    fallback_title=f"{normalized_units[0]['title']} guided session",
                    fallback_topics=[normalized_units[0]["title"]],
                    fallback_duration=context["time_budget"].get("value", 45),
                ),
            }

        if task_name == "plan_adjustment":
            current_micro_plan = context.get("current_micro_plan", {})
            target_unit = context.get("target_unit", {})
            fallback_unit_id = str(target_unit.get("id") or current_micro_plan.get("unit_id") or "unit-1")
            fallback_title = str(
                target_unit.get("title")
                or current_micro_plan.get("title")
                or "Adjusted study session"
            ).strip()
            fallback_topics = target_unit.get("topics") or current_micro_plan.get("topics") or [fallback_title]
            fallback_duration = current_micro_plan.get("estimated_duration", context.get("time_budget", {}).get("value", 45))
            return {
                "micro_plan": OpenAICompatibleProvider._normalize_micro_plan_payload(
                    payload.get("micro_plan", {}),
                    fallback_unit_id=fallback_unit_id,
                    fallback_title=fallback_title,
                    fallback_topics=fallback_topics,
                    fallback_duration=fallback_duration,
                ),
                "adjustment_summary": str(
                    payload.get("adjustment_summary")
                    or f"Adjusted micro plan for {context.get('adjustment_mode', 'learning')}."
                ).strip(),
            }

        if task_name == "learning_reply":
            reply = payload.get("reply") or payload.get("response") or payload.get("answer") or ""
            session_summary = payload.get("session_summary") or f"The learner explored '{context['message']}' within {context['micro_plan']['title']}."
            mastery_signals = payload.get("mastery_signals")
            if not isinstance(mastery_signals, list) or not mastery_signals:
                mastery_signals = ["follow_up_question_answered", "grounded_in_current_micro_plan"]
            return {
                "reply": str(reply).strip(),
                "session_summary": str(session_summary).strip(),
                "mastery_signals": [str(item).strip() for item in mastery_signals if str(item).strip()],
            }

        if task_name == "plan_assistant_reply":
            reply = payload.get("reply") or payload.get("response") or ""
            summary = payload.get("conversation_summary") or context.get("message") or ""
            if not reply:
                reply = (
                    "我收到你的规划目标了。你可以继续补充当前基础、可投入时长或偏好的学习方式，"
                    "我会结合已有信息整理成学习计划。"
                )
            return {
                "reply": str(reply).strip(),
                "conversation_summary": str(summary).strip(),
            }

        if task_name == "assessment_generation":
            return OpenAICompatibleProvider._normalize_assessment_payload(payload, context)

        if task_name == "subjective_evaluation":
            return OpenAICompatibleProvider._normalize_subjective_evaluation(payload, context)

        return payload

    @staticmethod
    def _normalize_micro_plan_payload(
        payload: dict[str, Any],
        *,
        fallback_unit_id: str,
        fallback_title: str,
        fallback_topics: list[str],
        fallback_duration: Any,
    ) -> dict[str, Any]:
        tasks_payload = payload.get("tasks")
        tasks = []
        if isinstance(tasks_payload, list):
            for index, task in enumerate(tasks_payload, start=1):
                if not isinstance(task, dict):
                    continue
                tasks.append(
                    {
                        "title": str(task.get("title") or f"Task {index}").strip(),
                        "status": str(task.get("status") or "pending").strip(),
                    }
                )
        if not tasks:
            tasks = [
                {"title": f"Review {fallback_title}", "status": "pending"},
                {"title": "Summarize the key idea in your own words", "status": "pending"},
            ]

        criteria_payload = payload.get("completion_criteria")
        completion_criteria = (
            [str(item).strip() for item in criteria_payload if str(item).strip()]
            if isinstance(criteria_payload, list)
            else []
        )
        if not completion_criteria:
            completion_criteria = [
                f"Explain {fallback_title} clearly",
                "Answer the follow-up assessment without hesitation",
            ]

        raw_topics = payload.get("topics")
        topics = [str(item).strip() for item in raw_topics if str(item).strip()] if isinstance(raw_topics, list) else []
        if not topics:
            topics = [str(item).strip() for item in fallback_topics if str(item).strip()] or [fallback_title]

        estimated_duration = payload.get("estimated_duration", fallback_duration)
        try:
            normalized_duration = max(1, int(round(float(estimated_duration))))
        except (TypeError, ValueError):
            normalized_duration = max(1, int(round(float(fallback_duration or 45))))

        assessment_trigger = payload.get("assessment_trigger")
        if not isinstance(assessment_trigger, dict):
            assessment_trigger = {"type": "after_session_complete", "minimum_tasks": min(2, len(tasks))}

        return {
            "unit_id": str(payload.get("unit_id") or fallback_unit_id).strip(),
            "title": str(payload.get("title") or fallback_title).strip(),
            "topics": topics,
            "estimated_duration": normalized_duration,
            "tasks": tasks,
            "completion_criteria": completion_criteria,
            "assessment_trigger": assessment_trigger,
        }

    @staticmethod
    def _normalize_assessment_payload(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        micro_plan = context.get("micro_plan", {})
        topics = micro_plan.get("topics", []) if isinstance(micro_plan.get("topics"), list) else []
        topics = [str(item).strip() for item in topics if str(item).strip()] or ["the current topic"]
        cue = context.get("knowledge_chunks", [])
        cue_text = ""
        if isinstance(cue, list) and cue:
            first_chunk = cue[0]
            if isinstance(first_chunk, dict):
                cue_text = str(first_chunk.get("content", "")).strip()[:120]
        assessment_type = str(context.get("assessment_type", "checkpoint")).strip() or "checkpoint"
        raw_questions = payload.get("questions") if isinstance(payload.get("questions"), list) else []

        raw_single_choice = [item for item in raw_questions if isinstance(item, dict) and item.get("question_type") == "single_choice"]
        raw_short_answer = [item for item in raw_questions if isinstance(item, dict) and item.get("question_type") == "short_answer"]

        questions = [
            OpenAICompatibleProvider._normalize_single_choice_question(
                raw_single_choice[index] if index < len(raw_single_choice) else {},
                index=index,
                topic=topics[index % len(topics)],
                cue_text=cue_text,
                assessment_type=assessment_type,
            )
            for index in range(SINGLE_CHOICE_QUESTION_COUNT)
        ]
        questions.extend(
            OpenAICompatibleProvider._normalize_short_answer_question(
                raw_short_answer[index] if index < len(raw_short_answer) else {},
                index=index,
                topic=topics[index % len(topics)],
                cue_text=cue_text,
                assessment_type=assessment_type,
            )
            for index in range(SHORT_ANSWER_QUESTION_COUNT)
        )

        scope = str(payload.get("scope") or "").strip() or {
            "checkpoint": "current_micro_plan",
            "unit": "current_unit",
            "final": "current_cycle",
        }.get(assessment_type, "current_micro_plan")
        difficulty = str(payload.get("difficulty") or "medium").strip()
        return {
            "scope": scope,
            "difficulty": difficulty,
            "questions": questions,
        }

    @staticmethod
    def _normalize_single_choice_question(
        payload: dict[str, Any],
        *,
        index: int,
        topic: str,
        cue_text: str,
        assessment_type: str,
    ) -> dict[str, Any]:
        default_correct = f"{topic}: focus on understanding before advancing"
        fallback_options = [
            default_correct,
            f"{topic}: skip review and rely on guessing",
            f"{topic}: ignore the core definition entirely",
            f"{topic}: move on without checking understanding",
        ]
        options_payload = payload.get("options") if isinstance(payload.get("options"), list) else []
        options = [str(item).strip() for item in options_payload if str(item).strip()]
        correct_answer = str(payload.get("correct_answer") or "").strip() or default_correct
        if correct_answer not in options:
            options = [correct_answer, *options]
        for option in fallback_options:
            if option not in options:
                options.append(option)
        options = options[:4]
        if correct_answer not in options:
            options[0] = correct_answer

        return {
            "question_type": "single_choice",
            "stem": str(payload.get("stem") or f"[{assessment_type}] Which statement best reflects the key idea of {topic}?").strip(),
            "options": options,
            "reference_scope": str(payload.get("reference_scope") or cue_text or topic).strip(),
            "expected_competency": str(payload.get("expected_competency") or f"Recognize the core idea of {topic}.").strip(),
            "points": SINGLE_CHOICE_POINTS,
            "correct_answer": correct_answer,
            "explanation": str(
                payload.get("explanation") or f"The correct option is the one that keeps the learner grounded in {topic} before moving on."
            ).strip(),
            "rubric": [],
        }

    @staticmethod
    def _normalize_short_answer_question(
        payload: dict[str, Any],
        *,
        index: int,
        topic: str,
        cue_text: str,
        assessment_type: str,
    ) -> dict[str, Any]:
        rubric_payload = payload.get("rubric") if isinstance(payload.get("rubric"), list) else []
        rubric = OpenAICompatibleProvider._normalize_rubric(rubric_payload, topic=topic, cue_text=cue_text)
        return {
            "question_type": "short_answer",
            "stem": str(
                payload.get("stem")
                or f"[{assessment_type}] Briefly explain the role of {topic} in the current study scope and how it supports the next step."
            ).strip(),
            "options": [],
            "reference_scope": str(payload.get("reference_scope") or cue_text or topic).strip(),
            "expected_competency": str(
                payload.get("expected_competency") or f"Explain {topic} clearly and connect it to the current study goal."
            ).strip(),
            "points": SHORT_ANSWER_POINTS,
            "correct_answer": "",
            "explanation": str(
                payload.get("explanation") or "Use the rubric to cover the core concept, its purpose, and its practical next-step meaning."
            ).strip(),
            "rubric": rubric,
        }

    @staticmethod
    def _normalize_rubric(payload: list[dict[str, Any]], *, topic: str, cue_text: str) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            criterion = str(item.get("criterion") or "").strip()
            if not criterion:
                continue
            try:
                points = max(0.0, float(item.get("points", 0)))
            except (TypeError, ValueError):
                points = 0.0
            keywords_payload = item.get("keywords") if isinstance(item.get("keywords"), list) else []
            keywords = [str(keyword).strip() for keyword in keywords_payload if str(keyword).strip()]
            normalized.append(
                {
                    "criterion": criterion,
                    "points": points,
                    "keywords": keywords,
                    "description": str(item.get("description") or "").strip(),
                }
            )

        if normalized:
            total_points = sum(item["points"] for item in normalized)
            if total_points > 0:
                scale = SHORT_ANSWER_POINTS / total_points
                for item in normalized:
                    item["points"] = round(item["points"] * scale, 2)
                rounded_total = round(sum(item["points"] for item in normalized), 2)
                if normalized and rounded_total != SHORT_ANSWER_POINTS:
                    normalized[-1]["points"] = round(normalized[-1]["points"] + (SHORT_ANSWER_POINTS - rounded_total), 2)
            return normalized

        fallback_keywords = OpenAICompatibleProvider._keyword_list(f"{topic} {cue_text}")
        concept_keywords = fallback_keywords[:2] or OpenAICompatibleProvider._keyword_list(topic) or [topic.lower()]
        use_keywords = fallback_keywords[2:4] or concept_keywords
        next_step_keywords = fallback_keywords[4:6] or concept_keywords
        return [
            {
                "criterion": "State the core concept accurately",
                "points": 2.0,
                "keywords": concept_keywords,
                "description": "Mention the central idea or definition.",
            },
            {
                "criterion": "Explain why it matters now",
                "points": 2.0,
                "keywords": use_keywords,
                "description": "Connect the concept to the current learning goal.",
            },
            {
                "criterion": "Link it to the next action",
                "points": 1.0,
                "keywords": next_step_keywords,
                "description": "Explain how understanding this supports the next micro study step.",
            },
        ]

    @staticmethod
    def _normalize_subjective_evaluation(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        rubric = context.get("rubric", []) if isinstance(context.get("rubric"), list) else []
        raw_results = payload.get("rubric_results") if isinstance(payload.get("rubric_results"), list) else []
        raw_results_by_criterion = {
            str(item.get("criterion", "")).strip(): item
            for item in raw_results
            if isinstance(item, dict) and str(item.get("criterion", "")).strip()
        }

        normalized_results = []
        for criterion in rubric:
            if not isinstance(criterion, dict):
                continue
            criterion_name = str(criterion.get("criterion") or "").strip()
            if not criterion_name:
                continue
            raw_result = raw_results_by_criterion.get(criterion_name, {})
            max_points = float(criterion.get("points", 0))
            try:
                earned_points = float(raw_result.get("earned_points", 0))
            except (TypeError, ValueError):
                earned_points = 0.0
            earned_points = max(0.0, min(max_points, earned_points))
            feedback = str(raw_result.get("feedback") or "").strip()
            if not feedback:
                feedback = (
                    "This rubric criterion was satisfied."
                    if earned_points >= max_points
                    else "This rubric criterion needs a clearer and more complete response."
                )
            normalized_results.append(
                {
                    "criterion": criterion_name,
                    "earned_points": round(earned_points, 2),
                    "max_points": round(max_points, 2),
                    "feedback": feedback,
                }
            )

        return {
            "rubric_results": normalized_results,
            "overall_feedback": str(
                payload.get("overall_feedback")
                or "Use the rubric feedback to improve the missing or weak parts of your explanation."
            ).strip(),
        }

    @staticmethod
    def _keyword_list(text: str) -> list[str]:
        ignored = {"the", "and", "for", "with", "this", "that", "from", "into", "your", "have"}
        tokens = [token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) > 3 and token not in ignored]
        unique = []
        for token in tokens:
            if token not in unique:
                unique.append(token)
        return unique


class FakeLLMProvider:
    _VECTOR_SIZE = 12

    def generate_structured(self, task_name: str, context: dict[str, Any]) -> dict[str, Any]:
        if task_name == "plan_generation":
            goal = context["learning_goals"].strip()
            assets = context.get("knowledge_assets", [])
            source_titles = [asset["title"] for asset in assets[:3]]
            source_hint = source_titles[0] if source_titles else "uploaded study materials"
            unit_title = self._title_from_goal(goal)
            next_unit_title = f"{unit_title} Practice"
            return {
                "macro_plan": {
                    "title": f"{unit_title} Learning Plan",
                    "goal": goal,
                    "duration": context["time_budget"],
                    "milestones": [
                        {"title": "Build foundations", "target": f"Understand the scope of {goal}"},
                        {"title": "Finish first checkpoint", "target": f"Use {source_hint} to complete a guided study loop"},
                        {"title": "Advance to the next micro study session", "target": f"Unlock {next_unit_title} through the stage test"},
                    ],
                    "units": [
                        {"id": "unit-1", "title": unit_title, "objective": f"Master the basics of {goal}"},
                        {"id": "unit-2", "title": next_unit_title, "objective": f"Apply {goal} in guided practice"},
                    ],
                },
                "micro_plan": {
                    "unit_id": "unit-1",
                    "title": f"{unit_title} guided session",
                    "topics": self._topics_from_context(goal, context.get("knowledge_chunks", [])),
                    "estimated_duration": max(30, int(context["time_budget"].get("value", 45))),
                    "tasks": [
                        {"title": f"Review the foundations of {goal}", "status": "pending"},
                        {"title": "Ask one clarifying question about the hardest point", "status": "pending"},
                        {"title": "Summarize the key idea in your own words", "status": "pending"},
                    ],
                    "completion_criteria": [
                        f"Explain the core idea of {goal} clearly",
                        "Answer at least one checkpoint question without hesitation",
                    ],
                    "assessment_trigger": {"type": "after_session_complete", "minimum_tasks": 2},
                },
            }

        if task_name == "learning_reply":
            message = context["message"].strip()
            topics = ", ".join(context["micro_plan"].get("topics", [])[:3])
            supporting_points = [chunk["content"] for chunk in context.get("knowledge_chunks", [])[:2]]
            support = " ".join(supporting_points).strip()
            reply = (
                f"Current focus: {context['micro_plan']['title']}. "
                f"Topics in scope: {topics or 'core concepts'}. "
                f"Question: {message}. "
            )
            if support:
                reply += f"Relevant notes: {support[:220]}."
            else:
                reply += "No indexed notes were available, so this explanation follows the active plan."
            return {
                "reply": reply.strip(),
                "session_summary": f"The learner explored '{message}' within {context['micro_plan']['title']}.",
                "mastery_signals": ["follow_up_question_answered", "grounded_in_current_micro_plan"],
            }

        if task_name == "plan_assistant_reply":
            message = context["message"].strip()
            previous_summary = str(context.get("conversation_summary", "")).strip()
            summary_parts = [part for part in [previous_summary, message] if part]
            conversation_summary = "；".join(summary_parts[-3:])
            return {
                "reply": (
                    f"收到，我会围绕“{message}”来整理学习计划。"
                    "如果你愿意，还可以继续补充当前基础、目标周期或偏好的学习风格。"
                ),
                "conversation_summary": conversation_summary,
            }

        if task_name == "assessment_generation":
            micro_plan = context["micro_plan"]
            topics = micro_plan.get("topics", ["the current topic"])
            topics = [str(item).strip() for item in topics if str(item).strip()] or ["the current topic"]
            primary_topic = topics[0]
            cue = context.get("knowledge_chunks", [])
            cue_text = cue[0]["content"][:80] if cue else primary_topic
            assessment_type = str(context.get("assessment_type", "checkpoint"))
            scope = {
                "checkpoint": "current_micro_plan",
                "unit": "current_unit",
                "final": "current_cycle",
            }.get(assessment_type, "current_micro_plan")
            questions: list[dict[str, Any]] = []
            for index in range(SINGLE_CHOICE_QUESTION_COUNT):
                topic = topics[index % len(topics)]
                correct_answer = f"{topic}: focus on understanding before advancing"
                questions.append(
                    {
                        "question_type": "single_choice",
                        "stem": f"[{assessment_type}] Which statement best reflects the key idea of {topic}?",
                        "options": [
                            correct_answer,
                            f"{topic}: skip review and rely on guessing",
                            f"{topic}: ignore the core definition entirely",
                            f"{topic}: move on without checking understanding",
                        ],
                        "reference_scope": cue_text or "current_micro_plan",
                        "expected_competency": f"Recognize the core idea of {topic}.",
                        "points": SINGLE_CHOICE_POINTS,
                        "correct_answer": correct_answer,
                        "explanation": f"The correct option keeps the learner grounded in {topic} before moving on.",
                        "rubric": [],
                    }
                )

            for index in range(SHORT_ANSWER_QUESTION_COUNT):
                topic = topics[index % len(topics)]
                questions.append(
                    {
                        "question_type": "short_answer",
                        "stem": f"[{assessment_type}] Briefly explain the role of {topic} in the current study scope and how it supports the next step.",
                        "options": [],
                        "reference_scope": cue_text or "current_micro_plan",
                        "expected_competency": f"Explain {topic} clearly and connect it to the current study goal.",
                        "points": SHORT_ANSWER_POINTS,
                        "correct_answer": "",
                        "explanation": "Use the rubric to cover the core concept, its purpose, and its practical next-step meaning.",
                        "rubric": OpenAICompatibleProvider._normalize_rubric([], topic=topic, cue_text=cue_text),
                    }
                )
            return {
                "scope": scope,
                "difficulty": "medium",
                "questions": questions,
            }

        if task_name == "plan_adjustment":
            mode = str(context.get("adjustment_mode", "remediation"))
            current_micro_plan = context.get("current_micro_plan", {})
            target_unit = context.get("target_unit", {})
            evaluation = context.get("evaluation", {})
            weak_areas = [
                item.get("area")
                for item in evaluation.get("mistake_analysis", [])
                if isinstance(item, dict) and item.get("area")
            ]
            base_title = str(target_unit.get("title") or current_micro_plan.get("title") or "Study session").strip()
            if mode == "next_unit":
                topics = self._keyword_set(f"{base_title} {target_unit.get('objective', '')}") or [base_title.lower()]
                return {
                    "micro_plan": {
                        "unit_id": str(target_unit.get("id") or current_micro_plan.get("unit_id") or "unit-1"),
                        "title": f"{base_title} guided session",
                        "topics": topics,
                        "estimated_duration": current_micro_plan.get("estimated_duration", 45),
                        "tasks": [
                            {"title": f"Learn the foundations of {base_title}", "status": "pending"},
                            {"title": "Ask one clarifying question about the toughest concept", "status": "pending"},
                            {"title": "Summarize the new unit objective in your own words", "status": "pending"},
                        ],
                        "completion_criteria": [
                            f"Explain the main idea of {base_title} clearly",
                            "Complete the next assessment without marked uncertainty",
                        ],
                        "assessment_trigger": {"type": "after_session_complete", "minimum_tasks": 2},
                    },
                    "adjustment_summary": f"Prepared the next micro plan for {base_title}.",
                }

            reinforcement_topics = list(dict.fromkeys([*current_micro_plan.get("topics", []), *weak_areas]))
            reinforcement_topics = reinforcement_topics[:4] or [base_title.lower()]
            return {
                "micro_plan": {
                    "unit_id": str(current_micro_plan.get("unit_id") or "unit-1"),
                    "title": f"{base_title} remediation session",
                    "topics": reinforcement_topics,
                    "estimated_duration": max(15, int(current_micro_plan.get("estimated_duration", 45))),
                    "tasks": [
                        {"title": "Revisit the weakest competency from the latest assessment", "status": "pending"},
                        {"title": "Rewrite the core concept in simpler words", "status": "pending"},
                        {"title": "Retry one focused practice question", "status": "pending"},
                    ],
                    "completion_criteria": [
                        "Can explain the weak concept without guessing",
                        "Can answer the next assessment with fewer uncertainties",
                    ],
                    "assessment_trigger": {"type": "after_session_complete", "minimum_tasks": 2},
                },
                "adjustment_summary": f"Updated the micro plan for remediation after the {context.get('assessment_type', 'latest')} assessment.",
            }

        if task_name == "subjective_evaluation":
            answer = str(context["answer"]).lower()
            rubric = context.get("rubric", []) if isinstance(context.get("rubric"), list) else []
            rubric_results = []
            total_points = 0.0
            earned_points = 0.0
            for criterion in rubric:
                if not isinstance(criterion, dict):
                    continue
                criterion_name = str(criterion.get("criterion", "")).strip()
                max_points = float(criterion.get("points", 0))
                keywords = [str(keyword).lower() for keyword in criterion.get("keywords", []) if str(keyword).strip()]
                matched = [keyword for keyword in keywords if keyword in answer]
                criterion_points = max_points if matched else 0.0
                total_points += max_points
                earned_points += criterion_points
                rubric_results.append(
                    {
                        "criterion": criterion_name,
                        "earned_points": criterion_points,
                        "max_points": max_points,
                        "feedback": (
                            "This part of the answer is covered clearly."
                            if matched
                            else "This part is missing or too vague."
                        ),
                    }
                )
            return {
                "rubric_results": rubric_results,
                "overall_feedback": (
                    "Answer covers the required rubric points."
                    if total_points and earned_points >= total_points
                    else "Answer needs a clearer connection to the rubric criteria."
                ),
            }

        raise AppError(500, "UNKNOWN_LLM_TASK", f"Unsupported fake LLM task: {task_name}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._VECTOR_SIZE
        for token in self._tokenize(text):
            slot = sum(ord(char) for char in token) % self._VECTOR_SIZE
            vector[slot] += 1.0
        length = max(1.0, sum(vector))
        return [value / length for value in vector]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if token]

    @staticmethod
    def _title_from_goal(goal: str) -> str:
        parts = [part for part in re.split(r"[^a-zA-Z0-9]+", goal.title()) if part]
        return " ".join(parts[:4]) or "Focused Study"

    def _topics_from_context(self, goal: str, chunks: list[dict[str, Any]]) -> list[str]:
        keywords = self._keyword_set(goal)
        for chunk in chunks:
            keywords.extend(self._keyword_set(chunk["content"]))
        unique = []
        for keyword in keywords:
            if keyword not in unique:
                unique.append(keyword)
            if len(unique) == 4:
                break
        return unique or ["overview", "core_concepts", "practice"]

    def _keyword_set(self, text: str) -> list[str]:
        ignored = {"the", "and", "for", "with", "this", "that", "from", "into", "your", "have"}
        tokens = [token for token in self._tokenize(text) if len(token) > 3 and token not in ignored]
        return tokens[:6]


def build_llm_provider(settings: Settings) -> LLMProviderAdapter:
    if settings.enable_real_llm and settings.llm_provider != "openai-compatible-stub":
        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "",
            model=settings.llm_model,
            embedding_model=settings.embedding_model,
            allow_fake_embedding_fallback=settings.enable_fake_embedding_fallback,
        )
    return FakeLLMProvider()
