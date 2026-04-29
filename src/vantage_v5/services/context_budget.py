from __future__ import annotations

from typing import Any


def build_context_budget_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a human-readable receipt for the context included in a turn."""

    response_mode = _mapping(payload.get("response_mode"))
    answer_basis = _mapping(payload.get("answer_basis"))
    answer_counts = _mapping(answer_basis.get("counts"))
    context_sources = _context_sources(response_mode, answer_basis)
    recall_items = _record_list(payload.get("recall") or payload.get("working_memory"))
    workspace = _mapping(payload.get("workspace"))
    interpretation = _mapping(payload.get("turn_interpretation"))

    recall_count = _count(
        answer_counts.get("recalled_items"),
        response_mode.get("recall_count"),
        response_mode.get("working_memory_count"),
        len(recall_items),
    )
    protocol_count = _count(
        answer_counts.get("protocol"),
        answer_counts.get("protocols"),
        sum(1 for item in recall_items if _is_protocol_item(item)),
    )
    memory_count = _count(
        answer_counts.get("memory"),
        max(0, recall_count - protocol_count),
    )
    trace_count = sum(1 for item in recall_items if _source(item) == "memory_trace")
    whiteboard_included = "whiteboard" in context_sources
    recent_chat_included = "recent_chat" in context_sources
    pending_whiteboard_included = "pending_whiteboard" in context_sources
    workspace_scope = _clean(workspace.get("context_scope"))
    pinned_preserved = _bool(
        interpretation.get("preserve_pinned_context")
        if "preserve_pinned_context" in interpretation
        else interpretation.get("preserve_selected_record")
    )
    pinned_reason = _clean(
        interpretation.get("pinned_context_reason")
        or interpretation.get("selected_record_reason")
    )

    rows = [
        _row(
            "user_request",
            "User request",
            included=True,
            detail="The current user message is always included.",
        ),
        _row(
            "recall",
            "Recall",
            included=recall_count > 0,
            count=recall_count,
            detail=(
                f"{_plural(recall_count, 'item')} entered Recall."
                if recall_count > 0
                else "No recalled Library or Memory Trace item entered Recall."
            ),
        ),
        _row(
            "protocol",
            "Protocols",
            included=protocol_count > 0,
            count=protocol_count,
            detail=(
                f"{_plural(protocol_count, 'protocol')} shaped the task as guidance."
                if protocol_count > 0
                else "No reusable protocol guidance was applied."
            ),
        ),
        _row(
            "whiteboard",
            "Whiteboard",
            included=whiteboard_included,
            count=1 if whiteboard_included else 0,
            scope=_workspace_scope_label(workspace_scope),
            detail=_whiteboard_detail(
                included=whiteboard_included,
                workspace_scope=workspace_scope,
            ),
        ),
        _row(
            "recent_chat",
            "Recent chat",
            included=recent_chat_included,
            count=1 if recent_chat_included else 0,
            detail=(
                "Recent conversation context was included."
                if recent_chat_included
                else "Recent chat was not included as a separate grounding source."
            ),
        ),
        _row(
            "pending_whiteboard",
            "Prior draft",
            included=pending_whiteboard_included,
            count=1 if pending_whiteboard_included else 0,
            detail=(
                "A prior pending whiteboard draft was included."
                if pending_whiteboard_included
                else "No prior pending whiteboard draft was included."
            ),
        ),
        _row(
            "pinned_context",
            "Pinned context",
            included=pinned_preserved is True,
            count=1 if pinned_preserved is True else 0,
            detail=(
                pinned_reason
                if pinned_preserved is True and pinned_reason
                else "Pinned context stayed in scope."
                if pinned_preserved is True
                else "No pinned context was preserved for this turn."
            ),
        ),
    ]
    if trace_count > 0:
        rows.append(
            _row(
                "memory_trace",
                "Memory Trace",
                included=True,
                count=trace_count,
                detail=f"{_plural(trace_count, 'recent history item')} entered Recall.",
            )
        )

    included_parts = [_row_summary(row) for row in rows if row["status"] == "included"]
    summary = (
        f"Context budget: {', '.join(included_parts)}."
        if included_parts
        else "Context budget: current request only."
    )
    return {
        "label": "Context Budget",
        "summary": summary,
        "rows": rows,
        "items": rows,
        "counts": {
            "recall": recall_count,
            "memory": memory_count,
            "protocol": protocol_count,
            "whiteboard": 1 if whiteboard_included else 0,
            "recent_chat": 1 if recent_chat_included else 0,
            "pending_whiteboard": 1 if pending_whiteboard_included else 0,
            "pinned_context": 1 if pinned_preserved is True else 0,
            "memory_trace": trace_count,
        },
        "context_sources": context_sources,
    }


def _row(
    key: str,
    label: str,
    *,
    included: bool,
    detail: str,
    count: int | None = None,
    scope: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "key": key,
        "label": label,
        "status": "included" if included else "excluded",
        "display_status": "Included" if included else "Excluded",
        "detail": detail,
    }
    if count is not None:
        row["count"] = count
    if scope:
        row["scope"] = scope
    return row


def _context_sources(response_mode: dict[str, Any], answer_basis: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    for source in _list(response_mode.get("context_sources")) or _list(response_mode.get("grounding_sources")):
        _append_source(sources, source)
    for source in _list(answer_basis.get("context_sources")):
        _append_source(sources, source)
    for source in _list(answer_basis.get("guidance_sources")):
        _append_source(sources, source)
    return sources


def _append_source(sources: list[str], value: Any) -> None:
    source = _normalized_source(value)
    if source and source not in sources:
        sources.append(source)


def _normalized_source(value: Any) -> str:
    source = str(value or "").strip().lower()
    if source in {"working_memory", "memory"}:
        return "recall"
    if source in {"recall", "protocol", "whiteboard", "recent_chat", "pending_whiteboard"}:
        return source
    return ""


def _whiteboard_detail(*, included: bool, workspace_scope: str | None) -> str:
    scope = _workspace_scope_label(workspace_scope)
    if included and scope:
        return f"Whiteboard content was included. Scope hint: {scope}."
    if included:
        return "Whiteboard content was included."
    if scope:
        return f"Whiteboard scope hint was {scope}, but it was not listed as a generation source."
    return "No whiteboard content was included."


def _workspace_scope_label(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    labels = {
        "visible": "Visible",
        "pinned": "Pinned",
        "requested": "Requested",
        "auto": "Auto",
    }
    return labels.get(normalized)


def _row_summary(row: dict[str, Any]) -> str:
    label = str(row.get("label") or "").strip() or "Context"
    count = row.get("count")
    if isinstance(count, int) and count > 0 and row.get("key") not in {"user_request", "whiteboard", "recent_chat", "pending_whiteboard", "pinned_context"}:
        return f"{label}: {count}"
    return label


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _record_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _count(*values: Any) -> int:
    for value in values:
        try:
            if value is None or value == "":
                continue
            return max(0, int(value))
        except (TypeError, ValueError):
            continue
    return 0


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "1", "yes", "included", "preserved"}:
        return True
    if normalized in {"false", "0", "no", "excluded", "not_preserved"}:
        return False
    return None


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _source(item: dict[str, Any]) -> str:
    return str(item.get("source") or item.get("type") or "").strip().lower()


def _is_protocol_item(item: dict[str, Any]) -> bool:
    if isinstance(item.get("protocol"), dict) and item["protocol"]:
        return True
    metadata = item.get("metadata")
    if isinstance(metadata, dict) and str(metadata.get("protocol_kind") or "").strip():
        return True
    return any(
        str(item.get(field) or "").strip().lower() == "protocol"
        for field in ("type", "kind", "memory_role")
    ) or str(item.get("source_tier") or "").strip().lower() == "instruction"


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"
