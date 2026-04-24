from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import AgentDecisionEntity, AgentTaskEntity


def extract_topic(question_stem: str) -> str:
    marker = "role of "
    suffix = " in the current study scope"
    lowered = question_stem.lower()
    if marker in lowered and suffix in lowered:
        start = lowered.index(marker) + len(marker)
        end = lowered.index(suffix)
        return question_stem[start:end].strip()
    return "the current topic"


def create_profile(client: TestClient, *, learning_goals: str = "Learn probability") -> None:
    client.post(
        "/api/profile",
        json={
            "learning_goals": learning_goals,
            "subject_scope": "math",
            "current_level": "beginner",
            "time_budget": {"unit": "day", "value": 45},
            "preferred_style": "practical",
            "preferred_difficulty": "medium",
            "preferred_question_types": ["single_choice", "short_answer"],
            "behavior_summary": "",
        },
    )


def generate_plan(client: TestClient, *, learning_goals: str = "Learn probability", attached_asset_ids: list[str] | None = None):
    return client.post(
        "/api/plans/generate",
        json={
            "learning_goals": learning_goals,
            "time_budget": {"unit": "day", "value": 45},
            "current_level": "beginner",
            "preferred_style": "practical",
            "preferred_difficulty": "medium",
            "preferred_question_types": ["single_choice", "short_answer"],
            "attached_asset_ids": attached_asset_ids or [],
        },
    )


def start_learning_loop(client: TestClient, *, micro_plan_id: str, message: str = "Explain the active topic simply") -> tuple[str, str]:
    session = client.post("/api/learning/session/start", json={"micro_plan_id": micro_plan_id})
    session_id = session.json()["id"]
    client.post("/api/learning/session/message", json={"session_id": session_id, "message": message})
    client.post(
        "/api/learning/session/complete",
        json={"session_id": session_id, "completion_signals": ["learner_confirmed", "phase3_acceptance"]},
    )
    assessment = client.post("/api/assessments/generate", json={"linked_plan_id": micro_plan_id, "type": "checkpoint"})
    return session_id, assessment.json()["id"]


def submit_assessment(client: TestClient, assessment_id: str, *, correct: bool = True, uncertain: bool = False):
    assessment_detail = client.get(f"/api/assessments/{assessment_id}").json()
    single_choice_questions = [question for question in assessment_detail["questions"] if question["question_type"] == "single_choice"]
    short_answer_questions = [question for question in assessment_detail["questions"] if question["question_type"] == "short_answer"]
    answers = []
    uncertainties = []
    if correct:
        answers.extend(
            {
                "question_id": question["id"],
                "answer": question["options"][0],
            }
            for question in single_choice_questions
        )
        answers.extend(
            {
                "question_id": question["id"],
                "answer": (
                    f"{extract_topic(question['stem'])} supports the current study scope by clarifying the core idea "
                    "and preparing the learner for the next micro study step."
                ),
            }
            for question in short_answer_questions
        )
    else:
        answers.extend(
            {
                "question_id": question["id"],
                "answer": question["options"][1] if len(question["options"]) > 1 else question["options"][0],
            }
            for question in single_choice_questions[:4]
        )
        if uncertain and short_answer_questions:
            uncertainties.append(short_answer_questions[0]["id"])
    return client.post(
        f"/api/assessments/{assessment_id}/submit",
        json={
            "answers": answers,
            "uncertainties": uncertainties,
        },
    )


def test_health_and_empty_states(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}
    assert client.get("/api/workflow/current").json()["current_stage"] == "onboarding"
    assert client.get("/api/plans").json() == {"plans": []}
    assert client.get("/api/plans/current").json() == {"macro_plan": None, "current_micro_plan": None}
    assert client.get("/api/knowledge/assets").json() == {"assets": []}


def test_profile_upsert_and_fetch(client: TestClient) -> None:
    payload = {
        "learning_goals": "Master probability basics",
        "subject_scope": "math",
        "current_level": "beginner",
        "time_budget": {"unit": "day", "value": 60},
        "preferred_style": "rigorous",
        "preferred_difficulty": "medium",
        "preferred_question_types": ["single_choice"],
        "behavior_summary": "",
    }

    created = client.post("/api/profile", json=payload)
    fetched = client.get("/api/profile")

    assert created.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json()["learning_goals"] == payload["learning_goals"]


def test_knowledge_upload_limits_and_retry_behavior(client: TestClient) -> None:
    unsupported = client.post(
        "/api/knowledge/assets",
        files=[("files", ("notes.docx", b"binary", "application/octet-stream"))],
    )
    assert unsupported.status_code == 415
    assert unsupported.json()["code"] == "UNSUPPORTED_FORMAT"

    failed = client.post("/api/knowledge/assets", files=[("files", ("empty.md", b"", "text/markdown"))])
    asset_id = failed.json()["assets"][0]["id"]
    assert failed.status_code == 200
    assert failed.json()["assets"][0]["status"] == "parse_failed"

    first_retry = client.post(f"/api/knowledge/assets/{asset_id}/retry")
    second_retry = client.post(f"/api/knowledge/assets/{asset_id}/retry")

    assert first_retry.status_code == 200
    assert second_retry.status_code == 409
    assert second_retry.json()["code"] == "RETRY_LIMIT_EXCEEDED"


def test_deleted_assets_are_excluded_from_search(client: TestClient) -> None:
    uploaded = client.post(
        "/api/knowledge/assets",
        files=[("files", ("notes.md", b"probability baseline concept", "text/markdown"))],
    )
    asset_id = uploaded.json()["assets"][0]["id"]

    assert client.get("/api/knowledge/search", params={"query": "probability"}).json()["chunks"]
    delete_response = client.delete(f"/api/knowledge/assets/{asset_id}")
    assert delete_response.status_code == 200
    assert client.get("/api/knowledge/search", params={"query": "probability"}).json()["chunks"] == []


def test_contract_stub_learning_loop(client: TestClient) -> None:
    profile_payload = {
        "learning_goals": "Learn SQL",
        "subject_scope": "databases",
        "current_level": "beginner",
        "time_budget": {"unit": "day", "value": 45},
        "preferred_style": "practical",
        "preferred_difficulty": "medium",
        "preferred_question_types": ["single_choice", "short_answer"],
        "behavior_summary": "",
    }
    client.post("/api/profile", json=profile_payload)

    generated_plan = client.post(
        "/api/plans/generate",
        json={
            "learning_goals": "Learn SQL",
            "time_budget": {"unit": "day", "value": 45},
            "current_level": "beginner",
            "preferred_style": "practical",
            "preferred_difficulty": "medium",
            "preferred_question_types": ["single_choice"],
            "attached_asset_ids": [],
        },
    )
    micro_plan_id = generated_plan.json()["current_micro_plan"]["id"]

    session = client.post("/api/learning/session/start", json={"micro_plan_id": micro_plan_id})
    session_id = session.json()["id"]
    message = client.post("/api/learning/session/message", json={"session_id": session_id, "message": "Explain joins simply"})
    complete = client.post("/api/learning/session/complete", json={"session_id": session_id, "completion_signals": ["learner_confirmed"]})

    assessment = client.post("/api/assessments/generate", json={"linked_plan_id": micro_plan_id, "type": "checkpoint"})
    assessment_id = assessment.json()["id"]
    submitted = submit_assessment(client, assessment_id)
    result = client.get(f"/api/assessments/{assessment_id}/result")

    assert generated_plan.status_code == 200
    assert session.status_code == 200
    assert message.status_code == 200
    assert complete.status_code == 200
    assert assessment.status_code == 200
    assert submitted.status_code == 200
    assert result.status_code == 200
    assert result.json()["score"] >= 0.8
    assert len(assessment.json()["questions"]) == 12
    assert assessment.json()["questions"][0]["points"] == 2
    assert assessment.json()["questions"][-1]["points"] == 5
    assert result.json()["passed"] is True
    assert len(result.json()["question_results"]) == 12
    assert client.get("/api/workflow/current").json()["current_stage"] == "learning"


def test_assessment_detail_can_be_reloaded_before_submission(client: TestClient) -> None:
    client.post(
        "/api/profile",
        json={
            "learning_goals": "Learn statistics",
            "subject_scope": "math",
            "current_level": "beginner",
            "time_budget": {"unit": "day", "value": 30},
            "preferred_style": "practical",
            "preferred_difficulty": "medium",
            "preferred_question_types": ["single_choice"],
            "behavior_summary": "",
        },
    )
    generated_plan = client.post(
        "/api/plans/generate",
        json={
            "learning_goals": "Learn statistics",
            "time_budget": {"unit": "day", "value": 30},
            "current_level": "beginner",
            "preferred_style": "practical",
            "preferred_difficulty": "medium",
            "preferred_question_types": ["single_choice"],
            "attached_asset_ids": [],
        },
    )
    micro_plan_id = generated_plan.json()["current_micro_plan"]["id"]
    _, assessment_id = start_learning_loop(client, micro_plan_id=micro_plan_id)

    fetched = client.get(f"/api/assessments/{assessment_id}")
    missing = client.get("/api/assessments/missing-assessment")

    assert fetched.status_code == 200
    assert fetched.json()["id"] == assessment_id
    assert len(fetched.json()["questions"]) == 12
    assert fetched.json()["questions"][0]["points"] == 2
    assert fetched.json()["questions"][-1]["points"] == 5
    assert fetched.json()["questions"][-1]["rubric"]
    assert missing.status_code == 404
    assert missing.json()["code"] == "ASSESSMENT_NOT_FOUND"


def test_phase1_loop_records_agent_audit_entries(client: TestClient, db_session) -> None:
    client.post(
        "/api/profile",
        json={
            "learning_goals": "Learn probability",
            "subject_scope": "math",
            "current_level": "beginner",
            "time_budget": {"unit": "day", "value": 30},
            "preferred_style": "rigorous",
            "preferred_difficulty": "medium",
            "preferred_question_types": ["single_choice"],
            "behavior_summary": "",
        },
    )
    client.post(
        "/api/knowledge/assets",
        files=[("files", ("notes.md", b"Probability fundamentals and conditional probability.", "text/markdown"))],
    )
    generated_plan = client.post(
        "/api/plans/generate",
        json={
            "learning_goals": "Learn probability",
            "time_budget": {"unit": "day", "value": 30},
            "current_level": "beginner",
            "preferred_style": "rigorous",
            "preferred_difficulty": "medium",
            "preferred_question_types": ["single_choice"],
            "attached_asset_ids": [],
        },
    )
    micro_plan_id = generated_plan.json()["current_micro_plan"]["id"]
    session = client.post("/api/learning/session/start", json={"micro_plan_id": micro_plan_id})
    client.post("/api/learning/session/message", json={"session_id": session.json()["id"], "message": "Explain conditional probability"})
    client.post("/api/learning/session/complete", json={"session_id": session.json()["id"], "completion_signals": ["learner_confirmed"]})
    client.post("/api/assessments/generate", json={"linked_plan_id": micro_plan_id, "type": "checkpoint"})

    tasks = list(db_session.scalars(select(AgentTaskEntity).order_by(AgentTaskEntity.created_at)).all())
    decisions = list(db_session.scalars(select(AgentDecisionEntity).order_by(AgentDecisionEntity.created_at)).all())

    assert [task.target_agent for task in tasks] == ["plan_agent", "input_agent", "output_agent"]
    assert len(decisions) == 3
    assert all(decision.artifacts for decision in decisions)


def test_invalid_workflow_transition_is_rejected(client: TestClient) -> None:
    response = client.post("/api/workflow/advance", json={"next_stage": "final_test", "reason": "skip ahead"})

    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_WORKFLOW_TRANSITION"


def test_phase3_plan_generation_uses_ready_assets_context(client: TestClient) -> None:
    create_profile(client, learning_goals="Learn Bayesian thinking")
    uploaded = client.post(
        "/api/knowledge/assets",
        files=[("files", ("bayes-notes.md", b"Bayesian reasoning updates beliefs with evidence.", "text/markdown"))],
        data={"title": "Bayes Notes"},
    )
    asset_id = uploaded.json()["assets"][0]["id"]

    generated = generate_plan(
        client,
        learning_goals="Learn Bayesian thinking",
        attached_asset_ids=[asset_id],
    )

    assert generated.status_code == 200
    assert "Bayes Notes" in generated.json()["macro_plan"]["milestones"][1]["target"]


def test_phase3_happy_path_tracks_workflow_history_and_current_plan(client: TestClient) -> None:
    create_profile(client)
    uploaded = client.post(
        "/api/knowledge/assets",
        files=[("files", ("probability-notes.md", b"Probability basics and conditional probability.", "text/markdown"))],
        data={"title": "Probability Notes"},
    )
    asset_id = uploaded.json()["assets"][0]["id"]
    generated = generate_plan(client, attached_asset_ids=[asset_id])
    generated_plan = generated.json()
    micro_plan_id = generated_plan["current_micro_plan"]["id"]
    macro_plan_id = generated_plan["macro_plan"]["id"]
    _, assessment_id = start_learning_loop(client, micro_plan_id=micro_plan_id, message="Explain conditional probability")

    submit = submit_assessment(client, assessment_id)
    workflow = client.get("/api/workflow/current").json()
    current_plan = client.get("/api/plans/current").json()

    assert submit.status_code == 200
    assert workflow["current_stage"] == "learning"
    assert workflow["recent_assessment_id"] == assessment_id
    assert workflow["current_macro_plan_id"] == macro_plan_id
    assert workflow["current_micro_plan_id"] != micro_plan_id
    assert current_plan["macro_plan"]["id"] == macro_plan_id
    assert current_plan["current_micro_plan"]["id"] == workflow["current_micro_plan_id"]
    assert {"from": "onboarding", "to": "planning", "reason": "Planning artifacts are being prepared."} in workflow["stage_history"]
    assert {"from": "planning", "to": "learning", "reason": "Plan generated and learning can start now."} in workflow["stage_history"]
    assert workflow["stage_history"][-1]["from"] == "checkpoint_test"
    assert workflow["stage_history"][-1]["to"] == "learning"
    assert workflow["stage_history"][-1]["reason"].startswith("Checkpoint cleared. Continue with ")


def test_plan_list_and_detail_show_current_plan_and_history(client: TestClient) -> None:
    create_profile(client, learning_goals="Learn Python")
    first_plan = generate_plan(client, learning_goals="Learn Python basics").json()
    second_plan = generate_plan(client, learning_goals="Prepare for CET-6").json()

    plan_list = client.get("/api/plans")
    first_detail = client.get(f"/api/plans/{first_plan['macro_plan']['id']}")
    second_detail = client.get(f"/api/plans/{second_plan['macro_plan']['id']}")

    assert plan_list.status_code == 200
    assert [plan["id"] for plan in plan_list.json()["plans"]] == [
        second_plan["macro_plan"]["id"],
        first_plan["macro_plan"]["id"],
    ]
    assert plan_list.json()["plans"][0]["is_current"] is True
    assert plan_list.json()["plans"][0]["current_micro_plan_title"] == second_plan["current_micro_plan"]["title"]
    assert first_detail.status_code == 200
    assert first_detail.json()["macro_plan"]["id"] == first_plan["macro_plan"]["id"]
    assert first_detail.json()["is_current"] is False
    assert len(first_detail.json()["micro_plans"]) == 1
    assert second_detail.json()["current_micro_plan_id"] == second_plan["current_micro_plan"]["id"]
    assert second_detail.json()["is_current"] is True


def test_plan_can_be_switched_and_current_plan_updates(client: TestClient) -> None:
    create_profile(client, learning_goals="Learn Python")
    first_plan = generate_plan(client, learning_goals="Learn Python basics").json()
    second_plan = generate_plan(client, learning_goals="Prepare for CET-6").json()

    activated = client.post(f"/api/plans/{first_plan['macro_plan']['id']}/activate")
    workflow = client.get("/api/workflow/current").json()
    current_plan = client.get("/api/plans/current").json()
    plan_list = client.get("/api/plans").json()

    assert activated.status_code == 200
    assert activated.json()["macro_plan"]["id"] == first_plan["macro_plan"]["id"]
    assert activated.json()["current_micro_plan"]["id"] == first_plan["current_micro_plan"]["id"]
    assert workflow["current_macro_plan_id"] == first_plan["macro_plan"]["id"]
    assert workflow["current_micro_plan_id"] == first_plan["current_micro_plan"]["id"]
    assert workflow["current_stage"] == "learning"
    assert current_plan["macro_plan"]["id"] == first_plan["macro_plan"]["id"]
    assert plan_list["plans"][0]["id"] == first_plan["macro_plan"]["id"]
    assert plan_list["plans"][0]["is_current"] is True
    assert any(plan["id"] == second_plan["macro_plan"]["id"] and not plan["is_current"] for plan in plan_list["plans"])


def test_plan_can_be_deleted_and_hidden_from_list(client: TestClient) -> None:
    create_profile(client, learning_goals="Learn Python")
    first_plan = generate_plan(client, learning_goals="Learn Python basics").json()
    second_plan = generate_plan(client, learning_goals="Prepare for CET-6").json()

    deleted = client.delete(f"/api/plans/{second_plan['macro_plan']['id']}")
    plan_list = client.get("/api/plans").json()
    current_plan = client.get("/api/plans/current").json()
    missing_detail = client.get(f"/api/plans/{second_plan['macro_plan']['id']}")

    assert deleted.status_code == 200
    assert deleted.json()["message"] == "Plan deleted."
    assert [plan["id"] for plan in plan_list["plans"]] == [first_plan["macro_plan"]["id"]]
    assert current_plan["macro_plan"]["id"] == first_plan["macro_plan"]["id"]
    assert missing_detail.status_code == 404
    assert missing_detail.json()["code"] == "PLAN_NOT_FOUND"


def test_deleting_current_plan_switches_to_latest_remaining_plan(client: TestClient) -> None:
    create_profile(client, learning_goals="Learn Python")
    first_plan = generate_plan(client, learning_goals="Learn Python basics").json()
    second_plan = generate_plan(client, learning_goals="Prepare for CET-6").json()

    deleted = client.delete(f"/api/plans/{second_plan['macro_plan']['id']}")
    workflow = client.get("/api/workflow/current").json()
    current_plan = client.get("/api/plans/current").json()

    assert deleted.status_code == 200
    assert workflow["current_macro_plan_id"] == first_plan["macro_plan"]["id"]
    assert workflow["current_micro_plan_id"] == first_plan["current_micro_plan"]["id"]
    assert workflow["current_stage"] == "learning"
    assert workflow["stage_history"][-1] == {
        "from": "learning",
        "to": "learning",
        "reason": f"Current plan deleted. Switched to {first_plan['macro_plan']['title']}.",
    }
    assert current_plan["macro_plan"]["id"] == first_plan["macro_plan"]["id"]


def test_plan_assistant_flow_generates_plan_from_conversation_and_ready_assets(client: TestClient) -> None:
    create_profile(client, learning_goals="Fallback learner goal")
    client.post(
        "/api/knowledge/assets",
        files=[("files", ("bayes-notes.md", b"Bayesian reasoning updates beliefs with evidence.", "text/markdown"))],
        data={"title": "Bayes Notes"},
    )

    session = client.post("/api/plans/assistant/sessions")
    session_id = session.json()["id"]
    message = client.post(
        f"/api/plans/assistant/sessions/{session_id}/messages",
        json={"message": "我想准备考研数学，希望 8 周内完成第一轮复习"},
    )
    generated = client.post(f"/api/plans/assistant/sessions/{session_id}/generate")
    current_plan = client.get("/api/plans/current")

    assert session.status_code == 200
    assert session.json()["conversation_turns"][0]["role"] == "assistant"
    assert message.status_code == 200
    assert "8 周内完成第一轮复习" in message.json()["session"]["conversation_summary"]
    assert generated.status_code == 200
    assert generated.json()["session"]["status"] == "generated"
    assert generated.json()["macro_plan"]["goal"] == "我想准备考研数学，希望 8 周内完成第一轮复习"
    assert generated.json()["macro_plan"]["duration"] == {"value": 8, "unit": "week"}
    assert "Bayes Notes" in generated.json()["macro_plan"]["milestones"][1]["target"]
    assert current_plan.json()["macro_plan"]["id"] == generated.json()["macro_plan"]["id"]


def test_plan_assistant_generate_requires_profile(client: TestClient) -> None:
    session = client.post("/api/plans/assistant/sessions")
    session_id = session.json()["id"]
    response = client.post(f"/api/plans/assistant/sessions/{session_id}/generate")

    assert response.status_code == 404
    assert response.json()["code"] == "PROFILE_NOT_FOUND"


def test_phase3_checkpoint_uncertainty_returns_workflow_to_learning(client: TestClient) -> None:
    create_profile(client)
    generated = generate_plan(client)
    micro_plan_id = generated.json()["current_micro_plan"]["id"]
    _, assessment_id = start_learning_loop(client, micro_plan_id=micro_plan_id)
    submit = submit_assessment(client, assessment_id, correct=False, uncertain=True)
    workflow = client.get("/api/workflow/current").json()

    assert submit.status_code == 200
    assert submit.json()["evaluation"]["score"] < 0.8
    assert workflow["current_stage"] == "learning"
    assert workflow["recent_assessment_id"] == assessment_id
    assert workflow["stage_history"][-1] == {
        "from": "checkpoint_test",
        "to": "learning",
        "reason": "Stage assessment not cleared. Continue the current micro study session.",
    }


def test_assessment_generation_rejects_stage_mismatch(client: TestClient) -> None:
    create_profile(client)
    generated = generate_plan(client)
    micro_plan_id = generated.json()["current_micro_plan"]["id"]

    response = client.post("/api/assessments/generate", json={"linked_plan_id": micro_plan_id, "type": "checkpoint"})

    assert response.status_code == 409
    assert response.json()["code"] == "ASSESSMENT_TYPE_STAGE_MISMATCH"


def test_phase4_flow_progresses_through_unit_and_final_stages(client: TestClient) -> None:
    create_profile(client)
    generated = generate_plan(client)
    first_micro_plan_id = generated.json()["current_micro_plan"]["id"]
    _, first_checkpoint_id = start_learning_loop(client, micro_plan_id=first_micro_plan_id)

    first_submit = submit_assessment(client, first_checkpoint_id)
    after_first_checkpoint = client.get("/api/workflow/current").json()
    second_micro_plan_id = after_first_checkpoint["current_micro_plan_id"]
    _, second_checkpoint_id = start_learning_loop(client, micro_plan_id=second_micro_plan_id)
    second_submit = submit_assessment(client, second_checkpoint_id)
    after_second_checkpoint = client.get("/api/workflow/current").json()
    current_plan = client.get("/api/plans/current").json()

    assert first_submit.status_code == 200
    assert after_first_checkpoint["current_stage"] == "learning"
    assert second_micro_plan_id != first_micro_plan_id
    assert second_submit.status_code == 200
    assert after_second_checkpoint["current_stage"] == "next_cycle"
    assert current_plan["macro_plan"]["status"] == "completed"


def test_phase4_unit_failure_replans_current_micro_plan(client: TestClient) -> None:
    create_profile(client)
    generated = generate_plan(client)
    original_micro_plan = generated.json()["current_micro_plan"]
    _, checkpoint_id = start_learning_loop(client, micro_plan_id=original_micro_plan["id"])

    checkpoint_submit = submit_assessment(client, checkpoint_id, correct=False, uncertain=True)
    workflow = client.get("/api/workflow/current").json()
    updated_micro_plan = client.get("/api/plans/current").json()["current_micro_plan"]

    assert checkpoint_submit.status_code == 200
    assert workflow["current_stage"] == "learning"
    assert workflow["stage_history"][-1] == {
        "from": "checkpoint_test",
        "to": "learning",
        "reason": "Stage assessment not cleared. Continue the current micro study session.",
    }
    assert updated_micro_plan["id"] == original_micro_plan["id"]
    assert updated_micro_plan["title"] != original_micro_plan["title"]
