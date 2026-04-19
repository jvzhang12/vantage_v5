from __future__ import annotations

from pathlib import Path

from vantage_v5.storage.markdown_store import MarkdownRecord
from vantage_v5.storage.markdown_store import MarkdownRecordStore
from vantage_v5.storage.markdown_store import slugify


ConceptRecord = MarkdownRecord


class ConceptStore(MarkdownRecordStore):
    def __init__(self, concepts_dir: Path) -> None:
        super().__init__(
            concepts_dir,
            source="concept",
            default_type="concept",
            trust="high",
        )

    def list_concepts(self) -> list[ConceptRecord]:
        return self.list_records()

    def create_concept(self, **kwargs) -> ConceptRecord:
        return self.create_record(**kwargs)

    def create_revision(self, *, base_concept_id: str, **kwargs) -> ConceptRecord:
        return super().create_revision(base_record_id=base_concept_id, **kwargs)
