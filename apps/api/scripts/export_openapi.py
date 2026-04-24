from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API_ROOT = ROOT / "apps" / "api"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.main import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    output = ROOT / "packages" / "contracts" / "openapi.json"
    output.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
