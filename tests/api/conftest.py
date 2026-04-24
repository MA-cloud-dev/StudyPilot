from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app


def run_migrations(database_url: str) -> None:
    config = Config("apps/api/alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.fixture
def migrated_db_url(tmp_path: Path) -> str:
    database_path = tmp_path / "studypilot-test.db"
    url = f"sqlite:///{database_path}"
    run_migrations(url)
    return url


@pytest.fixture(autouse=True)
def force_fake_runtime(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("STUDYPILOT_ENABLE_REAL_LLM", "false")
    monkeypatch.setenv("STUDYPILOT_LLM_PROVIDER", "openai-compatible-stub")
    monkeypatch.setenv("STUDYPILOT_LLM_MODEL", "stub-model")
    monkeypatch.setenv("STUDYPILOT_EMBEDDING_MODEL", "stub-embedding-model")
    monkeypatch.setenv("STUDYPILOT_ENABLE_FAKE_EMBEDDING_FALLBACK", "true")
    monkeypatch.delenv("STUDYPILOT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("STUDYPILOT_LLM_BASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()


@pytest.fixture
def engine(migrated_db_url: str) -> Generator[Engine, None, None]:
    test_engine = create_engine(migrated_db_url, connect_args={"check_same_thread": False}, future=True)
    try:
        yield test_engine
    finally:
        test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def db_session(session_factory) -> Generator[Session, None, None]:
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(session_factory) -> Generator[TestClient, None, None]:

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
