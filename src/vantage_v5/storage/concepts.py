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

    def upsert_protocol(
        self,
        *,
        protocol_id: str,
        title: str,
        card: str,
        body: str,
        protocol_kind: str,
        variables: dict | None = None,
        applies_to: list[str] | None = None,
        metadata: dict | None = None,
    ) -> ConceptRecord:
        protocol_metadata = dict(metadata or {})
        protocol_metadata["protocol_kind"] = protocol_kind
        protocol_metadata["variables"] = variables or {}
        protocol_metadata["applies_to"] = applies_to or []
        protocol_metadata["modifiable"] = True
        return self._write_record(
            record_id=slugify(protocol_id) or "protocol",
            title=title,
            card=card,
            body=body,
            type="protocol",
            links_to=[],
            comes_from=[],
            status="active",
            metadata=protocol_metadata,
        )

    def create_revision(self, *, base_concept_id: str, **kwargs) -> ConceptRecord:
        return super().create_revision(base_record_id=base_concept_id, **kwargs)
