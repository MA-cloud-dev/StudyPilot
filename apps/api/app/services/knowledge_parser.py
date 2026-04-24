from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.schemas.enums import ParseErrorReason


@dataclass(slots=True)
class ParseResult:
    text: str
    error_reason: ParseErrorReason | None = None

    @property
    def ok(self) -> bool:
        return self.error_reason is None


class KnowledgeParser:
    def parse(self, file_path: Path, file_type: str) -> ParseResult:
        suffix = file_type.lower()
        raw = file_path.read_bytes()
        if not raw:
            return ParseResult(text="", error_reason=ParseErrorReason.EMPTY_CONTENT)

        if suffix in {".md", ".txt"}:
            text = raw.decode("utf-8", errors="ignore").strip()
            if not text:
                return ParseResult(text="", error_reason=ParseErrorReason.EMPTY_CONTENT)
            return ParseResult(text=text)

        if suffix == ".pdf":
            return self._parse_pdf(raw)

        return ParseResult(text="", error_reason=ParseErrorReason.UNSUPPORTED_FORMAT)

    def _parse_pdf(self, raw: bytes) -> ParseResult:
        extracted = self._extract_pdf_with_library(raw) or self._extract_pdf_fallback(raw)
        if not extracted:
            return ParseResult(text="", error_reason=ParseErrorReason.FILE_CORRUPTED)
        return ParseResult(text=extracted)

    def _extract_pdf_with_library(self, raw: bytes) -> str:
        try:
            from io import BytesIO

            from pypdf import PdfReader
        except Exception:
            return ""

        try:
            reader = PdfReader(BytesIO(raw))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception:
            return ""
        return "\n".join(page.strip() for page in pages if page.strip()).strip()

    def _extract_pdf_fallback(self, raw: bytes) -> str:
        text = raw.decode("latin-1", errors="ignore")
        matches = re.findall(r"\(([^()]*)\)\s*Tj", text)
        if not matches:
            matches = re.findall(r"\(([^()]*)\)", text)
        cleaned = [item.replace("\\(", "(").replace("\\)", ")").strip() for item in matches if item.strip()]
        return "\n".join(cleaned).strip()
