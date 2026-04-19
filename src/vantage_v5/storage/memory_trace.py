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


def _single_line(value: str) -> str:
    return " ".join(value.strip().split())
