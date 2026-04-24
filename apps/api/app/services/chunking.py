from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ChunkDocument:
    chunk_index: int
    content: str
    metadata: dict[str, int]


class ChunkingService:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str) -> list[ChunkDocument]:
        normalized = " ".join(text.split())
        if not normalized:
            return []

        chunks: list[ChunkDocument] = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        start = 0
        chunk_index = 0
        while start < len(normalized):
            end = min(len(normalized), start + self.chunk_size)
            content = normalized[start:end].strip()
            if content:
                chunks.append(
                    ChunkDocument(
                        chunk_index=chunk_index,
                        content=content,
                        metadata={"start": start, "end": end},
                    )
                )
                chunk_index += 1
            if end >= len(normalized):
                break
            start += step
        return chunks
