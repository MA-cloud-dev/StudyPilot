from __future__ import annotations

import json
from pathlib import Path

from app.main import create_app


def test_openapi_contains_required_route_groups() -> None:
    schema = create_app().openapi()
    paths = schema["paths"].keys()

    assert "/api/plans" in paths
    assert "/api/profile" in paths
    assert "/api/knowledge/assets" in paths
    assert "/api/plans/current" in paths
    assert "/api/plans/{plan_id}" in paths
    assert "/api/plans/assistant/sessions" in paths
    assert "/api/plans/assistant/sessions/{session_id}/messages" in paths
    assert "/api/learning/session/start" in paths
    assert "/api/assessments/{assessment_id}" in paths
    assert "/api/assessments/generate" in paths
    assert "/api/workflow/current" in paths


def test_openapi_snapshot_exists_and_contains_core_schemas() -> None:
    snapshot_path = Path("packages/contracts/openapi.json")
    document = json.loads(snapshot_path.read_text(encoding="utf-8"))
    schemas = document["components"]["schemas"]

    for required in [
        "UserProfile",
        "KnowledgeAsset",
        "MacroPlan",
        "MicroPlan",
        "PlanAssistantSession",
        "LearningSession",
        "Assessment",
        "Evaluation",
        "WorkflowState",
    ]:
        assert required in schemas
