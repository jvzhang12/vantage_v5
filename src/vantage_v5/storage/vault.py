from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
from typing import Any

import yaml


NON_WORD_RE = re.compile(r"\s+")


@dataclass(slots=True)
class VaultNoteRecord:
    id: str
    title: str
    type: str
    card: str
    body: str
    relative_path: str
    folder: str
    tags: list[str]
    modified_at: str
    path: Path

    @property
    def searchable_text(self) -> str:
        tags = " ".join(self.tags)
        return " ".join(
            part
            for part in [self.title, self.card, tags, self.relative_path, self.folder, self.body]
            if part
        )

    @property
    def source(self) -> str:
        return "vault_note"

    @property
    def trust(self) -> str:
        return "medium"

    @property
    def path_hint(self) -> str:
        return self.relative_path


class VaultNoteStore:
    def __init__(
        self,
        *,
        vault_root: Path | None,
        include_paths: list[str] | None = None,
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.vault_root = vault_root
        self.include_paths = [item.strip() for item in include_paths or [] if item.strip()]
        self.exclude_paths = [item.strip() for item in exclude_paths or [] if item.strip()]

    def is_enabled(self) -> bool:
        return bool(self.vault_root and self.vault_root.exists())

    def list_notes(self) -> list[VaultNoteRecord]:
        root = self.vault_root
        if not root or not root.exists():
            return []

        notes: list[VaultNoteRecord] = []
        for path in sorted(self._iter_markdown_files(root)):
            relative_path = path.relative_to(root).as_posix()
            if not self._is_included(relative_path):
                continue
            if self._is_excluded(relative_path):
                continue
            notes.append(self._load_note(path, relative_path))
        return notes

    def list_cards(self) -> list[dict[str, Any]]:
        return [self._to_card(note) for note in self.list_notes()]

    def get(self, note_id: str) -> VaultNoteRecord:
        for note in self.list_notes():
            if note.id == note_id:
                return note
        raise FileNotFoundError(f"Vault note '{note_id}' was not found.")

    def _iter_markdown_files(self, root: Path):
        yield from root.rglob("*.md")

    def _is_included(self, relative_path: str) -> bool:
        if not self.include_paths:
            return True
        return any(
            relative_path == include or relative_path.startswith(f"{include.rstrip('/')}/")
            for include in self.include_paths
        )

    def _is_excluded(self, relative_path: str) -> bool:
        return any(
            relative_path == exclude or relative_path.startswith(f"{exclude.rstrip('/')}/")
            for exclude in self.exclude_paths
        )

    def _load_note(self, path: Path, relative_path: str) -> VaultNoteRecord:
        text = path.read_text(encoding="utf-8")
        metadata, body = _split_frontmatter(text)
        cleaned_body = body.strip()
        title = _title_from_note(relative_path, metadata, cleaned_body)
        card = _card_from_note(cleaned_body, fallback=title)
        tags = _tags_from_note(metadata)
        stat = path.stat()
        folder = Path(relative_path).parent.as_posix()
        if folder == ".":
            folder = ""
        return VaultNoteRecord(
            id=_note_id(relative_path),
            title=title,
            type="vault_note",
            card=card,
            body=cleaned_body,
            relative_path=relative_path,
            folder=folder,
            tags=tags,
            modified_at=str(int(stat.st_mtime)),
            path=path,
        )

    @staticmethod
    def _to_card(note: VaultNoteRecord) -> dict[str, Any]:
        return {
            "id": note.id,
            "title": note.title,
            "type": note.type,
            "card": note.card,
            "body": note.body,
            "source": note.source,
            "trust": note.trust,
            "path": note.relative_path,
            "folder": note.folder,
            "tags": note.tags,
            "modified_at": note.modified_at,
        }


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    _, remainder = text.split("---\n", 1)
    if "\n---\n" not in remainder:
        return {}, text
    frontmatter_text, body = remainder.split("\n---\n", 1)
    return yaml.safe_load(frontmatter_text) or {}, body


def _title_from_note(relative_path: str, metadata: dict[str, Any], body: str) -> str:
    for key in ["title", "name"]:
        if metadata.get(key):
            return str(metadata[key]).strip()
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return Path(relative_path).stem.replace("-", " ").replace("_", " ").title()


def _card_from_note(body: str, *, fallback: str) -> str:
    lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("#") and not line.strip().startswith(">")
    ]
    if not lines:
        return fallback if fallback.endswith(".") else f"{fallback}."
    compact = NON_WORD_RE.sub(" ", " ".join(lines)).strip()
    sentence = compact.split(".", 1)[0].strip() if "." in compact else compact[:157].strip()
    if sentence and not sentence.endswith("."):
        sentence += "."
    return sentence[:180]


def _tags_from_note(metadata: dict[str, Any]) -> list[str]:
    tags = metadata.get("tags", []) or []
    if isinstance(tags, str):
        return [tags.strip()] if tags.strip() else []
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    return []


def _note_id(relative_path: str) -> str:
    digest = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:10]
    stem = Path(relative_path).stem.lower().replace(" ", "-")
    stem = re.sub(r"[^a-z0-9-]+", "-", stem).strip("-") or "vault-note"
    return f"vault-{stem}-{digest}"
