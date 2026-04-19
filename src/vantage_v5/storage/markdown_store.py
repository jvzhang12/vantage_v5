from __future__ import annotations

from dataclasses import dataclass
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

    @property
    def searchable_text(self) -> str:
        links = " ".join(self.links_to)
        lineage = " ".join(self.comes_from)
        return " ".join(
            part
            for part in [self.id, self.title, self.type, self.card, links, lineage, self.body]
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
    ) -> MarkdownRecord:
        base = self.get(base_record_id)
        record_id = self._next_revision_id(base.id)
        revision_links = list(dict.fromkeys([*(links_to or []), *base.links_to]))
        revision_lineage = list(dict.fromkeys([base.id, *(comes_from or [])]))
        return self._write_record(
            record_id=record_id,
            title=title.strip() or f"{base.title} Revision",
            card=card.strip() or base.card,
            body=body.strip(),
            type=base.type,
            links_to=revision_links,
            comes_from=revision_lineage,
            status="active",
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
    ) -> MarkdownRecord:
        self.records_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(tz=UTC).date().isoformat()
        metadata = {
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
        frontmatter = yaml.safe_dump(
            metadata,
            sort_keys=False,
            allow_unicode=False,
        ).strip()
        text = f"---\n{frontmatter}\n---\n\n{body.strip()}\n"
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
        )

    @staticmethod
    def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
        if not text.startswith("---\n"):
            return {}, text
        _, remainder = text.split("---\n", 1)
        frontmatter_text, body = remainder.split("\n---\n", 1)
        return yaml.safe_load(frontmatter_text) or {}, body


def slugify(value: str) -> str:
    normalized = SLUG_RE.sub("-", value.lower()).strip("-")
    return normalized
