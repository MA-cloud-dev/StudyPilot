from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.models import KnowledgeAssetEntity
from app.schemas.assessment import SubmissionAnswer
from app.schemas.enums import KnowledgeAssetStatus, ParseErrorReason
from app.services.chunking import ChunkingService
from app.services.knowledge_parser import KnowledgeParser
from app.services.knowledge_service import KnowledgeService
from app.services.llm_provider import FakeLLMProvider, OpenAICompatibleProvider
from app.services.retrieval import RetrievalProvider
from app.services.scoring import ScoringService


def test_chunking_service_preserves_overlap() -> None:
    service = ChunkingService(chunk_size=20, chunk_overlap=5)
    chunks = service.split("alpha beta gamma delta epsilon zeta eta theta iota")

    assert len(chunks) >= 2
    assert chunks[0].metadata["end"] > chunks[1].metadata["start"]


def test_knowledge_parser_supports_text_and_pdf_fallback(tmp_path: Path) -> None:
    parser = KnowledgeParser()
    markdown = tmp_path / "notes.md"
    markdown.write_text("# SQL joins\nInner join basics", encoding="utf-8")

    pdf = tmp_path / "notes.pdf"
    pdf.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\nstream\nBT\n(Probability basics and Bayes theorem) Tj\nET\nendstream\n%%EOF"
    )

    markdown_result = parser.parse(markdown, ".md")
    pdf_result = parser.parse(pdf, ".pdf")

    assert markdown_result.ok
    assert "SQL joins" in markdown_result.text
    assert pdf_result.ok
    assert "Probability basics" in pdf_result.text


def test_knowledge_parser_marks_empty_and_corrupted_content(tmp_path: Path) -> None:
    parser = KnowledgeParser()
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    broken_pdf = tmp_path / "broken.pdf"
    broken_pdf.write_bytes(b"%PDF-1.4\n%%%%")

    assert parser.parse(empty, ".txt").error_reason == ParseErrorReason.EMPTY_CONTENT
    assert parser.parse(broken_pdf, ".pdf").error_reason == ParseErrorReason.FILE_CORRUPTED


def test_retrieval_provider_indexes_searches_and_respects_soft_delete(db_session) -> None:
    settings = Settings()
    llm_provider = FakeLLMProvider()
    retrieval = RetrievalProvider(db_session, llm_provider, ChunkingService(chunk_size=40, chunk_overlap=10))
    parser = KnowledgeParser()
    service = KnowledgeService(db_session, settings, parser, retrieval)
    now = datetime.now(timezone.utc)

    asset = KnowledgeAssetEntity(
        id="asset-1",
        title="Probability Notes",
        source_type="upload",
        file_type=".md",
        file_size_bytes=32,
        status=KnowledgeAssetStatus.READY.value,
        parse_error_reason=None,
        retry_count=0,
        raw_path="storage/raw/asset-1.md",
        parsed_text="Probability baseline concept and conditional probability.",
        tags=["math", "probability"],
        chunks=[],
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    db_session.add(asset)
    db_session.flush()
    retrieval.index_asset(asset, asset.parsed_text)
    db_session.commit()

    results = service.search_assets("conditional probability", top_k=5, tags=["math"]).chunks
    assert results
    assert results[0].asset_id == "asset-1"

    asset.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert service.search_assets("conditional probability", top_k=5).chunks == []


def test_scoring_service_combines_objective_and_subjective_checks() -> None:
    scoring = ScoringService(FakeLLMProvider())
    outcome = scoring.evaluate(
        questions=[
            {"id": "q1", "question_type": "single_choice", "correct_answer": "A", "expected_competency": "recall"},
            {"id": "q2", "question_type": "short_answer", "rubric_keywords": ["probability"], "expected_competency": "explain"},
        ],
        answers=[
            SubmissionAnswer(question_id="q1", answer="A"),
            SubmissionAnswer(question_id="q2", answer="Probability matters because it quantifies uncertainty."),
        ],
        uncertainties=[],
    )

    assert outcome.score >= 0.8
    assert "Proceed" in outcome.recommendations[0] or "Review" in outcome.recommendations[0]


def test_scoring_service_returns_points_ratio_and_question_level_feedback() -> None:
    scoring = ScoringService(FakeLLMProvider())
    outcome = scoring.evaluate(
        questions=[
            {
                "id": "q1",
                "question_type": "single_choice",
                "correct_answer": "A",
                "expected_competency": "recall",
                "points": 2,
                "explanation": "Option A is the only answer that matches the core idea.",
            },
            {
                "id": "q2",
                "question_type": "short_answer",
                "expected_competency": "explain",
                "points": 5,
                "rubric": [
                    {"criterion": "State the key concept", "points": 3, "keywords": ["probability"]},
                    {"criterion": "Connect it to the next step", "points": 2, "keywords": ["next"]},
                ],
            },
        ],
        answers=[
            SubmissionAnswer(question_id="q1", answer="B"),
            SubmissionAnswer(question_id="q2", answer="Probability supports the next practice step."),
        ],
        uncertainties=[],
    )

    assert outcome.earned_points == 5.0
    assert outcome.total_points == 7.0
    assert outcome.score_ratio == 0.71
    assert outcome.passed is False
    assert len(outcome.question_results) == 2
    assert outcome.question_results[0].correct_answer == "A"
    assert outcome.question_results[0].error_reason == "The selected option does not match the correct answer."
    assert outcome.question_results[1].earned_points == 5.0
    assert len(outcome.question_results[1].rubric_results) == 2


def test_build_evaluation_uses_database_safe_id_length() -> None:
    scoring = ScoringService(FakeLLMProvider())
    outcome = scoring.evaluate(
        questions=[{"id": "q1", "question_type": "single_choice", "correct_answer": "A", "expected_competency": "recall"}],
        answers=[SubmissionAnswer(question_id="q1", answer="A")],
        uncertainties=[],
    )

    evaluation = scoring.build_evaluation("12345678-1234-1234-1234-123456789012", outcome)

    assert len(evaluation.id) == 36


def test_openai_provider_translates_timeout(monkeypatch) -> None:
    class DummyCompletions:
        def create(self, **_: object) -> object:
            raise TimeoutError("boom")

    class DummyChat:
        completions = DummyCompletions()

    class DummyClient:
        chat = DummyChat()

    monkeypatch.setattr(OpenAICompatibleProvider, "_build_client", lambda self: DummyClient())
    provider = OpenAICompatibleProvider(base_url=None, api_key="x", model="m", embedding_model="e")

    with pytest.raises(AppError) as exc:
        provider.generate_structured("plan_generation", {"learning_goals": "SQL"})

    assert exc.value.code == "LLM_TIMEOUT"


def test_openai_provider_can_fallback_to_fake_embeddings(monkeypatch) -> None:
    class DummyEmbeddings:
        def create(self, **_: object) -> object:
            raise RuntimeError("embedding endpoint unavailable")

    class DummyClient:
        embeddings = DummyEmbeddings()

    monkeypatch.setattr(OpenAICompatibleProvider, "_build_client", lambda self: DummyClient())
    provider = OpenAICompatibleProvider(
        base_url=None,
        api_key="x",
        model="m",
        embedding_model="missing-model",
        allow_fake_embedding_fallback=True,
    )

    embeddings = provider.embed_texts(["probability basics"])

    assert len(embeddings) == 1
    assert len(embeddings[0]) == FakeLLMProvider._VECTOR_SIZE


def test_openai_provider_normalizes_learning_reply_payload() -> None:
    payload = OpenAICompatibleProvider._normalize_payload(
        "learning_reply",
        {
            "response": "Here is the explanation.",
            "suggested_next_steps": ["review notes"],
        },
        {
            "message": "Why does this matter?",
            "micro_plan": {"title": "Demo Session", "topics": ["probability"]},
        },
    )

    assert payload["reply"] == "Here is the explanation."
    assert payload["session_summary"] == "The learner explored 'Why does this matter?' within Demo Session."
    assert payload["mastery_signals"] == ["follow_up_question_answered", "grounded_in_current_micro_plan"]
