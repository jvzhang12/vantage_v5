from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vantage_v5.storage.markdown_store import MarkdownRecord
from vantage_v5.storage.markdown_store import MarkdownRecordStore
from vantage_v5.storage.markdown_store import slugify


MemoryTraceRecord = MarkdownRecord


class MemoryTraceStore(MarkdownRecordStore):
    def __init__(self, memory_trace_dir: Path) -> None:
        super().__init__(
            memory_trace_dir,
            source="memory_trace",
            default_type="memory_trace",
            trust="medium",
        )

    def list_traces(self) -> list[MemoryTraceRecord]:
        return self.list_records()

    def list_recent_traces(self, *, limit: int = 24) -> list[MemoryTraceRecord]:
        records = self.list_records()
        records.sort(key=lambda record: record.path.stem, reverse=True)
        return records[:limit]

    def create_turn_trace(
        self,
        *,
        user_message: str,
        assistant_message: str,
        working_memory: list[dict[str, Any]],
        history: list[dict[str, str]],
        workspace_id: str,
        workspace_title: str,
        workspace_content: str | None,
        workspace_scope: str,
        learned: list[dict[str, Any]],
        response_mode: dict[str, Any],
        scope: str,
        pending_workspace_update: dict[str, Any] | None = None,
        turn_mode: str = "chat",
        preserved_context: dict[str, Any] | None = None,
        referenced_record: dict[str, Any] | None = None,
    ) -> MemoryTraceRecord:
        record_id = self._next_turn_trace_id(user_message)
        title = _turn_trace_title(user_message)
        card = _turn_trace_card(user_message, assistant_message)
        links_to = [
            str(item.get("id") or "").strip()
            for item in [*working_memory, *learned]
            if str(item.get("id") or "").strip()
        ]
        comes_from = [workspace_id] if workspace_id else []
        body = _render_turn_trace_body(
            user_message=user_message,
            assistant_message=assistant_message,
            working_memory=working_memory,
            history=history,
            workspace_title=workspace_title,
            workspace_content=workspace_content,
            workspace_scope=workspace_scope,
            learned=learned,
            response_mode=response_mode,
            scope=scope,
            pending_workspace_update=pending_workspace_update,
            preserved_context=preserved_context,
            referenced_record=referenced_record,
        )
        frontmatter = _turn_trace_frontmatter(
            workspace_id=workspace_id,
            workspace_title=workspace_title,
            workspace_scope=workspace_scope,
            response_mode=response_mode,
            scope=scope,
            history=history,
            working_memory=working_memory,
            learned=learned,
            pending_workspace_update=pending_workspace_update,
            turn_mode=turn_mode,
            preserved_context=preserved_context,
            referenced_record=referenced_record,
        )
        return self._write_record(
            record_id=record_id,
            title=title,
            card=card,
            body=body,
            type="memory_trace",
            links_to=links_to,
            comes_from=comes_from,
            status="active",
            metadata=frontmatter,
        )

    def _next_turn_trace_id(self, user_message: str) -> str:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S%f")
        base_slug = slugify(user_message)[:48] or "turn"
        return self._unique_id(f"turn-{timestamp}-{base_slug}")


def _turn_trace_title(user_message: str) -> str:
    summary = " ".join(user_message.strip().split())
    if not summary:
        return "Turn Trace"
    if len(summary) <= 72:
        return f"Turn Trace: {summary}"
    return f"Turn Trace: {summary[:69].rstrip()}..."


def _turn_trace_card(user_message: str, assistant_message: str) -> str:
    user_summary = " ".join(user_message.strip().split())
    assistant_summary = " ".join(assistant_message.strip().split())
    if assistant_summary:
        assistant_summary = assistant_summary[:140].rstrip()
    if user_summary and assistant_summary:
        return f"{user_summary[:96].rstrip()} -> {assistant_summary}"
    return user_summary[:160].rstrip() or assistant_summary or "Captured recent turn context."


def _render_turn_trace_body(
    *,
    user_message: str,
    assistant_message: str,
    working_memory: list[dict[str, Any]],
    history: list[dict[str, str]],
    workspace_title: str,
    workspace_content: str | None,
    workspace_scope: str,
    learned: list[dict[str, Any]],
    response_mode: dict[str, Any],
    scope: str,
    pending_workspace_update: dict[str, Any] | None,
    preserved_context: dict[str, Any] | None = None,
    referenced_record: dict[str, Any] | None = None,
) -> str:
    sections = [
        "# Memory Trace",
        "",
        "## User Message",
        user_message.strip() or "(empty)",
        "",
        "## Assistant Response",
        assistant_message.strip() or "(empty)",
        "",
        "## Working Memory",
    ]
    if working_memory:
        for item in working_memory:
            title = str(item.get("title") or item.get("id") or "Untitled").strip()
            source = str(item.get("source") or "record").strip()
            card = _single_line(str(item.get("card") or ""))
            if card:
                sections.append(f"- [{source}] {title}: {card[:180]}")
            else:
                sections.append(f"- [{source}] {title}")
    else:
        sections.append("- No recalled items were selected for this turn.")
    sections.extend(
        [
            "",
            "## Response Mode",
            f"- Kind: {response_mode.get('kind') or 'unknown'}",
            f"- Grounding mode: {response_mode.get('grounding_mode') or 'unknown'}",
            f"- Sources: {', '.join(response_mode.get('context_sources') or []) or 'none'}",
            f"- Recall count: {response_mode.get('recall_count') or 0}",
            "",
            "## Whiteboard Context",
            f"- Title: {workspace_title or 'Untitled whiteboard'}",
            f"- Scope: {workspace_scope or 'excluded'}",
            f"- Storage scope: {scope}",
        ]
    )
    if workspace_content:
        sections.append(f"- Excerpt: {_single_line(workspace_content[:240])}")
    else:
        sections.append("- Excerpt: none")
    sections.extend(
        [
            "",
            "## Recent Chat",
        ]
    )
    if history:
        for entry in history[-4:]:
            role = str(entry.get("role") or "unknown").strip() or "unknown"
            content = _single_line(str(entry.get("content") or ""))
            if content:
                sections.append(f"- {role}: {content[:180]}")
    else:
        sections.append("- No prior recent chat carried into this turn.")
    sections.extend(
        [
            "",
            "## Learned",
        ]
    )
    if learned:
        for item in learned:
            title = str(item.get("title") or item.get("id") or "Untitled").strip()
            source = str(item.get("source") or "record").strip()
            sections.append(f"- [{source}] {title}")
    else:
        sections.append("- Nothing new was learned or saved.")
    if preserved_context:
        context_title = str(preserved_context.get("title") or preserved_context.get("id") or "Untitled").strip()
        context_source = str(preserved_context.get("source") or "record").strip() or "record"
        sections.extend(
            [
                "",
                "## Preserved Context",
                f"- [{context_source}] {context_title}",
            ]
        )
    if referenced_record:
        record_title = str(referenced_record.get("title") or referenced_record.get("id") or "Untitled").strip()
        record_source = str(referenced_record.get("source") or "record").strip() or "record"
        sections.extend(
            [
                "",
                "## Referenced Record",
                f"- [{record_source}] {record_title}",
            ]
        )
    if pending_workspace_update:
        sections.extend(
            [
                "",
                "## Pending Whiteboard Context",
                f"- Status: {pending_workspace_update.get('status') or pending_workspace_update.get('type') or 'unknown'}",
                f"- Summary: {_single_line(str(pending_workspace_update.get('summary') or '')) or 'none'}",
            ]
    )
    return "\n".join(sections).strip() + "\n"


def _turn_trace_frontmatter(
    *,
    workspace_id: str,
    workspace_title: str,
    workspace_scope: str,
    response_mode: dict[str, Any],
    scope: str,
    history: list[dict[str, str]],
    working_memory: list[dict[str, Any]],
    learned: list[dict[str, Any]],
    pending_workspace_update: dict[str, Any] | None,
    turn_mode: str,
    preserved_context: dict[str, Any] | None,
    referenced_record: dict[str, Any] | None,
) -> dict[str, Any]:
    recalled_ids = [str(item.get("id") or "").strip() for item in working_memory if str(item.get("id") or "").strip()]
    recalled_sources = sorted(
        {
            str(item.get("source") or "").strip()
            for item in working_memory
            if str(item.get("source") or "").strip()
        }
    )
    learned_ids = [str(item.get("id") or "").strip() for item in learned if str(item.get("id") or "").strip()]
    learned_sources = sorted(
        {
            str(item.get("source") or "").strip()
            for item in learned
            if str(item.get("source") or "").strip()
        }
    )
    frontmatter: dict[str, Any] = {
        "trace_kind": "turn",
        "turn_mode": turn_mode.strip() or "chat",
        "trace_scope": scope,
        "workspace_id": workspace_id,
        "workspace_title": workspace_title,
        "workspace_scope": workspace_scope,
        "whiteboard_in_scope": workspace_scope == "visible",
        "response_mode_kind": response_mode.get("kind"),
        "grounding_mode": response_mode.get("grounding_mode") or response_mode.get("groundingMode"),
        "grounding_label": response_mode.get("label"),
        "context_sources": response_mode.get("context_sources") or response_mode.get("contextSources") or [],
        "recall_count": response_mode.get("recall_count") or response_mode.get("recallCount") or 0,
        "working_memory_count": response_mode.get("working_memory_count") or response_mode.get("workingMemoryCount") or 0,
        "history_count": len(history),
        "recalled_ids": recalled_ids,
        "recalled_sources": recalled_sources,
        "learned_count": len(learned),
        "learned_ids": learned_ids,
        "learned_sources": learned_sources,
    }
    if pending_workspace_update:
        frontmatter["pending_workspace_status"] = (
            pending_workspace_update.get("status") or pending_workspace_update.get("type") or "unknown"
        )
    if preserved_context:
        preserved_context_id = str(preserved_context.get("id") or "").strip()
        preserved_context_source = str(preserved_context.get("source") or "").strip()
        if preserved_context_id:
            frontmatter["preserved_context_id"] = preserved_context_id
        if preserved_context_source:
            frontmatter["preserved_context_source"] = preserved_context_source
    if referenced_record:
        referenced_record_id = str(referenced_record.get("id") or "").strip()
        referenced_record_title = str(referenced_record.get("title") or "").strip()
        referenced_record_source = str(referenced_record.get("source") or "").strip()
        if referenced_record_id:
            frontmatter["referenced_record_id"] = referenced_record_id
        if referenced_record_title:
            frontmatter["referenced_record_title"] = referenced_record_title
        if referenced_record_source:
            frontmatter["referenced_record_source"] = referenced_record_source
    return frontmatter


def parse_memory_trace_metadata(record: MemoryTraceRecord) -> dict[str, Any]:
    metadata = dict(record.metadata) if isinstance(getattr(record, "metadata", {}), dict) else {}
    workspace_scope = str(metadata.get("workspace_scope") or "").strip().lower()
    return {
        "trace_kind": str(metadata.get("trace_kind") or "turn").strip().lower() or "turn",
        "turn_mode": str(metadata.get("turn_mode") or "chat").strip().lower() or "chat",
        "trace_scope": str(metadata.get("trace_scope") or "").strip().lower(),
        "workspace_id": str(metadata.get("workspace_id") or "").strip(),
        "workspace_title": str(metadata.get("workspace_title") or "").strip(),
        "workspace_scope": workspace_scope,
        "whiteboard_in_scope": bool(metadata.get("whiteboard_in_scope")) if "whiteboard_in_scope" in metadata else workspace_scope == "visible",
        "grounding_mode": str(metadata.get("grounding_mode") or "").strip().lower(),
        "grounding_label": str(metadata.get("grounding_label") or "").strip(),
        "context_sources": _normalize_string_list(metadata.get("context_sources")),
        "recall_count": _normalize_int(metadata.get("recall_count")),
        "working_memory_count": _normalize_int(metadata.get("working_memory_count")),
        "history_count": _normalize_int(metadata.get("history_count")),
        "learned_count": _normalize_int(metadata.get("learned_count")),
        "recalled_ids": _normalize_string_list(metadata.get("recalled_ids")),
        "recalled_sources": _normalize_string_list(metadata.get("recalled_sources")),
        "learned_ids": _normalize_string_list(metadata.get("learned_ids")),
        "learned_sources": _normalize_string_list(metadata.get("learned_sources")),
        "pending_workspace_status": str(metadata.get("pending_workspace_status") or "").strip().lower(),
        "preserved_context_id": str(metadata.get("preserved_context_id") or "").strip(),
        "preserved_context_source": str(metadata.get("preserved_context_source") or "").strip().lower(),
    }


def _single_line(value: str) -> str:
    return " ".join(value.strip().split())


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
