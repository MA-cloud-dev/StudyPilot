from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings


def test_settings_parse_origins_and_create_storage_dirs(tmp_path: Path) -> None:
    settings = Settings(
        allowed_origins="http://localhost:3000, http://localhost:3001",
        storage_root=tmp_path / "storage",
        storage_raw_dir=tmp_path / "storage" / "raw",
        storage_parsed_dir=tmp_path / "storage" / "parsed",
        storage_temp_dir=tmp_path / "storage" / "temp",
    )

    settings.validate_runtime()

    assert settings.allowed_origins == ["http://localhost:3000", "http://localhost:3001"]
    assert (tmp_path / "storage" / "raw").exists()
    assert (tmp_path / "storage" / "parsed").exists()
    assert (tmp_path / "storage" / "temp").exists()


def test_settings_reject_non_positive_upload_limits(tmp_path: Path) -> None:
    settings = Settings(
        max_file_size_mb=0,
        storage_root=tmp_path / "storage",
        storage_raw_dir=tmp_path / "storage" / "raw",
        storage_parsed_dir=tmp_path / "storage" / "parsed",
        storage_temp_dir=tmp_path / "storage" / "temp",
    )

    with pytest.raises(ValueError):
        settings.validate_runtime()
