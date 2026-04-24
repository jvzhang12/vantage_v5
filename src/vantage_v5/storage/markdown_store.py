from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any

import yaml


SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(slots=True)
class MarkdownRecord:
    id: str
    title: str
    type: str
    card: str
    body: str
    status: str
    links_to: list[str]
    comes_from: list[str]
    path: Path
    source_value: str
    trust_value: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def searchable_text(self) -> str:
        links = " ".join(self.links_to)
        lineage = " ".join(self.comes_from)
        metadata = _metadata_text(self.metadata)
        return " ".join(
            part
            for part in [self.id, self.title, self.type, self.card, links, lineage, metadata, self.body]
            if part
        )

    @property
    def source(self) -> str:
        return self.source_value

    @property
    def trust(self) -> str:
        return self.trust_value

    @property
    def path_hint(self) -> str:
        return self.path.name


class MarkdownRecordStore:
    def __init__(
        self,
        records_dir: Path,
        *,
        source: str,
        default_type: str,
        trust: str,
    ) -> None:
        self.records_dir = records_dir
        self.source = source
        self.default_type = default_type
        self.trust = trust

    def get(self, record_id: str) -> MarkdownRecord:
        path = self.records_dir / f"{record_id}.md"
        if not path.exists():
            raise FileNotFoundError(f"{self.source.title()} '{record_id}' was not found.")
        return self._load_record(path)

    def list_records(self) -> list[MarkdownRecord]:
        records: list[MarkdownRecord] = []
        if not self.records_dir.exists():
            return records
        for path in sorted(self.records_dir.glob("*.md")):
            records.append(self._load_record(path))
        return records

    def list_cards(self) -> list[dict[str, Any]]:
        return [self._record_card(record) for record in self.list_records()]

    def create_record(
        self,
        *,
        title: str,
        card: str,
        body: str,
        type: str | None = None,
        links_to: list[str] | None = None,
        comes_from: list[str] | None = None,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> MarkdownRecord:
        record_id = self._unique_id(slugify(title) or self.default_type)
        return self._write_record(
            record_id=record_id,
            title=title.strip() or record_id.replace("-", " ").title(),
            card=card.strip(),
            body=body.strip(),
            type=type or self.default_type,
            links_to=links_to or [],
            comes_from=comes_from or [],
            status=status,
            metadata=metadata,
        )

    def create_revision(
        self,
        *,
        base_record_id: str,
        title: str,
        card: str,
        body: str,
        links_to: list[str] | None = None,
        comes_from: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MarkdownRecord:
        base = self.get(base_record_id)
        record_id = self._next_revision_id(base.id)
        revision_links = list(dict.fromkeys([*(links_to or []), *base.links_to]))
        revision_lineage = list(dict.fromkeys([base.id, *(comes_from or [])]))
        revision_metadata = dict(metadata or {})
        revision_metadata.setdefault("revision_of", base.id)
        return self._write_record(
            record_id=record_id,
            title=title.strip() or f"{base.title} Revision",
            card=card.strip() or base.card,
            body=body.strip(),
            type=base.type,
            links_to=revision_links,
            comes_from=revision_lineage,
            status="active",
            metadata=revision_metadata,
        )

    def _record_card(self, record: MarkdownRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "title": record.title,
            "type": record.type,
            "card": record.card,
            "body": record.body,
            "status": record.status,
            "links_to": record.links_to,
            "comes_from": record.comes_from,
            "filename": record.path.name,
            "source": record.source,
            "trust": record.trust,
        }

    def _write_record(
        self,
        *,
        record_id: str,
        title: str,
        card: str,
        body: str,
        type: str,
        links_to: list[str],
        comes_from: list[str],
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> MarkdownRecord:
        self.records_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(tz=UTC).date().isoformat()
        frontmatter = {
            "id": record_id,
            "title": title,
            "type": type,
            "card": card,
            "created_at": now,
            "updated_at": now,
            "links_to": links_to,
            "comes_from": comes_from,
            "status": status,
        }
        if metadata:
            for key, value in metadata.items():
                if value is not None and key not in frontmatter:
                    frontmatter[key] = value
        frontmatter_text = yaml.safe_dump(
            frontmatter,
            sort_keys=False,
            allow_unicode=False,
        ).strip()
        text = f"---\n{frontmatter_text}\n---\n\n{body.strip()}\n"
        path = self.records_dir / f"{record_id}.md"
        path.write_text(text, encoding="utf-8")
        return self._load_record(path)

    def _unique_id(self, base_id: str) -> str:
        record_id = base_id
        index = 2
        while (self.records_dir / f"{record_id}.md").exists():
            record_id = f"{base_id}-{index}"
            index += 1
        return record_id

    def _next_revision_id(self, base_id: str) -> str:
        index = 2
        while True:
            candidate = f"{base_id}--v{index}"
            if not (self.records_dir / f"{candidate}.md").exists():
                return candidate
            index += 1

    def _load_record(self, path: Path) -> MarkdownRecord:
        text = path.read_text(encoding="utf-8")
        metadata, body = self._split_frontmatter(text)
        links_to = metadata.get("links_to", []) or []
        if isinstance(links_to, str):
            links_to = [links_to]
        comes_from = metadata.get("comes_from", []) or []
        if isinstance(comes_from, str):
            comes_from = [comes_from]
        return MarkdownRecord(
            id=metadata.get("id", path.stem),
            title=metadata.get("title", path.stem),
            type=metadata.get("type", self.default_type),
            card=metadata.get("card", ""),
            body=body.strip(),
            status=metadata.get("status", "active"),
            links_to=list(links_to),
            comes_from=list(comes_from),
            path=path,
            source_value=self.source,
            trust_value=self.trust,
            metadata=_custom_metadata(metadata),
        )

    @staticmethod
    def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
        if not text.startswith("---\n"):
            return {}, text
        _, remainder = text.split("---\n", 1)
        frontmatter_text, body = remainder.split("\n---\n", 1)
        metadata = yaml.safe_load(frontmatter_text) or {}
        if not isinstance(metadata, dict):
            return {}, body
        return metadata, body


def slugify(value: str) -> str:
    normalized = SLUG_RE.sub("-", value.lower()).strip("-")
    return normalized


def _metadata_text(value: Any) -> str:
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            cleaned_key = _single_line(str(key))
            if cleaned_key:
                parts.append(cleaned_key)
            cleaned_item = _metadata_text(item)
            if cleaned_item:
                parts.append(cleaned_item)
        return " ".join(parts)
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            cleaned_item = _metadata_text(item)
            if cleaned_item:
                parts.append(cleaned_item)
        return " ".join(parts)
    if value is None:
        return ""
    return _single_line(str(value))


def _single_line(value: str) -> str:
    return " ".join(value.strip().split())


def _custom_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    reserved_keys = {
        "id",
        "title",
        "type",
        "card",
        "created_at",
        "updated_at",
        "links_to",
        "comes_from",
        "status",
    }
    return {
        key: value
        for key, value in metadata.items()
        if key not in reserved_keys
    }
