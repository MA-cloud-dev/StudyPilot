from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TMP_ROOT = ROOT / ".tmp" / "phase3-e2e"
DB_PATH = TMP_ROOT / "studypilot-e2e.db"
STORAGE_ROOT = TMP_ROOT / "storage"


def prepare_runtime() -> dict[str, str]:
    if TMP_ROOT.exists():
        shutil.rmtree(TMP_ROOT)
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

    api_port = os.environ.get("STUDYPILOT_E2E_API_PORT", "8010")
    allowed_origin = os.environ.get("STUDYPILOT_E2E_ALLOWED_ORIGIN", "http://127.0.0.1:3100")

    env = os.environ.copy()
    env.update(
        {
            "STUDYPILOT_DATABASE_URL": f"sqlite:///{DB_PATH.as_posix()}",
            "STUDYPILOT_API_HOST": "127.0.0.1",
            "STUDYPILOT_API_PORT": api_port,
            "STUDYPILOT_ALLOWED_ORIGINS": f'["{allowed_origin}"]',
            "STUDYPILOT_STORAGE_ROOT": str(STORAGE_ROOT),
            "STUDYPILOT_STORAGE_RAW_DIR": str(STORAGE_ROOT / "raw"),
            "STUDYPILOT_STORAGE_PARSED_DIR": str(STORAGE_ROOT / "parsed"),
            "STUDYPILOT_STORAGE_TEMP_DIR": str(STORAGE_ROOT / "temp"),
            "STUDYPILOT_ENABLE_REAL_LLM": "false",
            "STUDYPILOT_LLM_PROVIDER": "openai-compatible-stub",
            "STUDYPILOT_LLM_MODEL": "stub-model",
            "STUDYPILOT_EMBEDDING_MODEL": "stub-embedding-model",
        }
    )
    return env


def main() -> None:
    os.chdir(ROOT)
    env = prepare_runtime()
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"],
        check=True,
        cwd=ROOT,
        env=env,
    )

    os.environ.update(env)
    import uvicorn

    uvicorn.run(
        "app.main:app",
        app_dir="apps/api",
        host="127.0.0.1",
        port=int(env["STUDYPILOT_API_PORT"]),
        reload=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
