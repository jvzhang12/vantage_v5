from __future__ import annotations

from pathlib import Path

from vantage_v5.storage.markdown_store import MarkdownRecord
from vantage_v5.storage.markdown_store import MarkdownRecordStore


MemoryRecord = MarkdownRecord


class MemoryStore(MarkdownRecordStore):
    def __init__(self, memories_dir: Path) -> None:
        super().__init__(
            memories_dir,
            source="memory",
            default_type="memory",
            trust="medium",
        )

    def list_memories(self) -> list[MemoryRecord]:
        return self.list_records()

    def create_memory(self, **kwargs) -> MemoryRecord:
        return self.create_record(**kwargs)
