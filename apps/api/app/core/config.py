from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STUDYPILOT_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./studypilot.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    storage_root: Path = Path("storage")
    storage_raw_dir: Path = Path("storage/raw")
    storage_parsed_dir: Path = Path("storage/parsed")
    storage_temp_dir: Path = Path("storage/temp")
    max_file_size_mb: int = 20
    max_upload_batch_count: int = 10
    max_total_storage_mb: int = 500
    llm_provider: str = "openai-compatible-stub"
    llm_model: str = "stub-model"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    embedding_model: str = "stub-embedding-model"
    enable_real_llm: bool = False
    enable_fake_embedding_fallback: bool = False
    retrieval_top_k: int = 5
    assessment_mastery_threshold: float = 0.8
    chunk_size: int = 500
    chunk_overlap: int = 80

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("storage_root", "storage_raw_dir", "storage_parsed_dir", "storage_temp_dir", mode="before")
    @classmethod
    def parse_path(cls, value: str | Path) -> Path:
        return Path(value)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "Settings":
        if self.retrieval_top_k <= 0:
            raise ValueError("retrieval_top_k must be positive")
        if not 0 < self.assessment_mastery_threshold <= 1:
            raise ValueError("assessment_mastery_threshold must be between 0 and 1")
        if self.chunk_size <= 0 or self.chunk_overlap < 0:
            raise ValueError("chunk sizing values must be non-negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self

    def validate_runtime(self) -> None:
        if self.max_file_size_mb <= 0 or self.max_upload_batch_count <= 0 or self.max_total_storage_mb <= 0:
            raise ValueError("upload limits must be positive")
        if not self.database_url:
            raise ValueError("database_url is required")
        if not self.llm_provider or not self.llm_model:
            raise ValueError("llm provider configuration is required")
        if self.enable_real_llm and not self.llm_api_key:
            raise ValueError("llm api key is required when real llm mode is enabled")
        for directory in (self.storage_root, self.storage_raw_dir, self.storage_parsed_dir, self.storage_temp_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
