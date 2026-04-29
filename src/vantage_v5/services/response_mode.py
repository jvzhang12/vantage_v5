from __future__ import annotations

from typing import Any

from vantage_v5.services.search import CandidateMemory

BEST_GUESS_PREFACE = "This is new to me, but my best guess is:"


def build_answer_basis_payload(payload: dict[str, Any]) -> dict[str, Any]:
    recall_items = _recall_items(payload)
    excluded_ids = _current_turn_record_ids(payload)
    eligible_items = [
        item
        for item in recall_items
        if isinstance(item, dict) and _item_id(item) not in excluded_ids
    ]
    protocol_items = [item for item in eligible_items if _is_protocol_item(item)]
    memory_items = [item for item in eligible_items if not _is_protocol_item(item)]
    response_context_sources = _response_context_sources(payload)
    whiteboard_sources = [
        source
        for source in response_context_sources
        if source in {"whiteboard", "pending_whiteboard"}
    ]
    has_recent_chat = "recent_chat" in response_context_sources

    source_buckets: list[str] = []
    if memory_items:
        source_buckets.append("memory")
    if protocol_items:
        source_buckets.append("protocol")
    if whiteboard_sources:
        source_buckets.append("whiteboard")
    if has_recent_chat:
        source_buckets.append("conversation")

    context_sources = _answer_context_sources(
        memory_items=memory_items,
        protocol_items=protocol_items,
        whiteboard_sources=whiteboard_sources,
        has_recent_chat=has_recent_chat,
    )
    evidence_sources = _answer_evidence_sources(
        memory_items=memory_items,
        whiteboard_sources=whiteboard_sources,
        has_recent_chat=has_recent_chat,
    )
    guidance_sources = ["protocol"] if protocol_items else []
    counts = {
        "memory": len(memory_items),
        "protocol": len(protocol_items),
        "whiteboard": len(whiteboard_sources),
        "conversation": 1 if has_recent_chat else 0,
        "recalled_items": len(memory_items) + len(protocol_items),
    }
    kind, label = _answer_basis_kind_and_label(
        source_buckets=source_buckets,
        memory_count=len(memory_items),
        protocol_count=len(protocol_items),
        whiteboard_count=len(whiteboard_sources),
        has_recent_chat=has_recent_chat,
    )
    has_factual_grounding = bool(memory_items or whiteboard_sources or has_recent_chat)
    summary = _answer_basis_summary(
        kind,
        memory_count=len(memory_items),
        protocol_count=len(protocol_items),
        whiteboard_sources=whiteboard_sources,
        has_recent_chat=has_recent_chat,
        has_factual_grounding=has_factual_grounding,
    )
    return {
        "kind": kind,
        "label": label,
        "summary": summary,
        "note": summary,
        "has_factual_grounding": has_factual_grounding,
        "sources": context_sources,
        "context_sources": context_sources,
        "evidence_sources": evidence_sources,
        "guidance_sources": guidance_sources,
        "counts": counts,
    }


def build_response_mode_payload(
    vetted_memory: list[CandidateMemory],
    *,
    workspace_has_context: bool,
    history_has_context: bool,
    pending_workspace_has_context: bool = False,
) -> dict[str, Any]:
    context_sources = _context_sources(
        vetted_memory,
        workspace_has_context=workspace_has_context,
        history_has_context=history_has_context,
        pending_workspace_has_context=pending_workspace_has_context,
    )
    legacy_context_sources = [_legacy_context_source(source) for source in context_sources]
    grounding_mode = _grounding_mode(
        vetted_memory,
        workspace_has_context=workspace_has_context,
        history_has_context=history_has_context,
        pending_workspace_has_context=pending_workspace_has_context,
    )
    legacy_grounding_mode = _legacy_grounding_mode(grounding_mode)
    count = len(vetted_memory)
    if grounding_mode != "ungrounded":
        return {
            "kind": "grounded",
            "label": _response_mode_label(grounding_mode, context_sources, count),
            "grounding_mode": grounding_mode,
            "legacy_grounding_mode": legacy_grounding_mode,
            "grounding_sources": context_sources,
            "context_sources": context_sources,
            "legacy_grounding_sources": legacy_context_sources,
            "legacy_context_sources": legacy_context_sources,
            "recall_count": count,
            "working_memory_count": count,
            "note": _response_mode_note(grounding_mode, context_sources, count),
        }
    return {
        "kind": "best_guess",
        "label": "Best Guess",
        "grounding_mode": "ungrounded",
        "legacy_grounding_mode": "ungrounded",
        "grounding_sources": context_sources,
        "context_sources": context_sources,
        "legacy_grounding_sources": legacy_context_sources,
        "legacy_context_sources": legacy_context_sources,
        "recall_count": 0,
        "working_memory_count": 0,
        "note": _response_mode_note("ungrounded", context_sources, 0),
    }


def finalize_assistant_message(
    assistant_message: str,
    *,
    response_mode: dict[str, Any],
    suppress_best_guess_preface: bool = False,
) -> str:
    text = assistant_message.strip()
    if response_mode.get("kind") != "best_guess":
        return text
    if suppress_best_guess_preface:
        return text
    if not text:
        return BEST_GUESS_PREFACE
    if text.startswith(BEST_GUESS_PREFACE):
        return text
    return f"{BEST_GUESS_PREFACE}\n\n{text}"


def _grounding_mode(
    vetted_memory: list[CandidateMemory],
    *,
    workspace_has_context: bool,
    history_has_context: bool,
    pending_workspace_has_context: bool = False,
) -> str:
    if vetted_memory:
        if workspace_has_context or history_has_context or pending_workspace_has_context:
            return "mixed_context"
        return "recall"

    active_contexts = sum(
        1 for flag in (workspace_has_context, history_has_context, pending_workspace_has_context) if flag
    )
    if active_contexts >= 2:
        return "mixed_context"
    if workspace_has_context:
        return "whiteboard"
    if history_has_context:
        return "recent_chat"
    if pending_workspace_has_context:
        return "pending_whiteboard"
    return "ungrounded"


def _context_sources(
    vetted_memory: list[CandidateMemory],
    *,
    workspace_has_context: bool,
    history_has_context: bool,
    pending_workspace_has_context: bool = False,
) -> list[str]:
    context_sources: list[str] = []
    if vetted_memory:
        context_sources.append("recall")
    if workspace_has_context:
        context_sources.append("whiteboard")
    if history_has_context:
        context_sources.append("recent_chat")
    if pending_workspace_has_context:
        context_sources.append("pending_whiteboard")
    return context_sources


def _legacy_grounding_mode(grounding_mode: str) -> str:
    if grounding_mode == "recall":
        return "working_memory"
    return grounding_mode


def _legacy_context_source(source: str) -> str:
    if source == "recall":
        return "working_memory"
    return source


def _response_mode_label(grounding_mode: str, context_sources: list[str], recall_count: int) -> str:
    if grounding_mode == "recall":
        return "Recall"
    if grounding_mode == "whiteboard":
        return "Whiteboard"
    if grounding_mode == "recent_chat":
        return "Recent Chat"
    if grounding_mode == "pending_whiteboard":
        return "Prior Whiteboard"
    if grounding_mode == "mixed_context":
        return _describe_context_sources(context_sources, style="label") or "Mixed Context"
    if grounding_mode == "ungrounded":
        return "Best Guess"
    return "Recall" if recall_count > 0 else "Grounded"


def _response_mode_note(grounding_mode: str, context_sources: list[str], recall_count: int) -> str:
    if grounding_mode == "ungrounded":
        return "No grounded context supported this answer."
    if grounding_mode == "recall":
        return (
            f"Supported by {recall_count} recalled item{'s' if recall_count != 1 else ''} "
            "from Recall."
        )
    if grounding_mode == "whiteboard":
        return "Supported by the active whiteboard."
    if grounding_mode == "recent_chat":
        return "Supported by the recent conversation."
    if grounding_mode == "pending_whiteboard":
        return "Supported by the prior whiteboard."
    if grounding_mode == "mixed_context":
        context_note = _describe_context_sources(context_sources, style="note")
        return f"Supported by {context_note}." if context_note else "Supported by multiple context sources."
    return "Supported by available context."


def _describe_context_sources(context_sources: list[str], *, style: str = "note") -> str:
    label_map = {
        "recall": "Recall",
        "working_memory": "Recall",
        "whiteboard": "Whiteboard",
        "recent_chat": "Recent Chat",
        "pending_whiteboard": "Prior Whiteboard",
    }
    note_map = {
        "recall": "Recall",
        "working_memory": "Recall",
        "whiteboard": "the active whiteboard",
        "recent_chat": "the recent conversation",
        "pending_whiteboard": "the prior whiteboard",
    }
    values = label_map if style == "label" else note_map
    labels = [values[source] for source in context_sources if source in values]
    if not labels:
        return ""
    if style == "label":
        return " + ".join(labels)
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + f" and {labels[-1]}"


def _recall_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    recall = payload.get("recall")
    if isinstance(recall, list):
        return [item for item in recall if isinstance(item, dict)]
    working_memory = payload.get("working_memory")
    if isinstance(working_memory, list):
        return [item for item in working_memory if isinstance(item, dict)]
    return []


def _current_turn_record_ids(payload: dict[str, Any]) -> set[str]:
    record_ids: set[str] = set()
    for record in payload.get("learned") or []:
        if isinstance(record, dict):
            record_id = _item_id(record)
            if record_id:
                record_ids.add(record_id)
    created_record = payload.get("created_record")
    if isinstance(created_record, dict):
        record_id = _item_id(created_record)
        if record_id:
            record_ids.add(record_id)
    return record_ids


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("record_id") or item.get("concept_id") or "").strip()


def _is_protocol_item(item: dict[str, Any]) -> bool:
    protocol_metadata = item.get("protocol")
    if isinstance(protocol_metadata, dict) and protocol_metadata:
        return True
    metadata = item.get("metadata")
    if isinstance(metadata, dict) and str(metadata.get("protocol_kind") or "").strip():
        return True
    return any(
        _normalized_metadata_value(item.get(field)) == "protocol"
        for field in ("type", "kind", "memory_role")
    ) or _normalized_metadata_value(item.get("source_tier")) == "instruction"


def _normalized_metadata_value(value: Any) -> str:
    return str(value or "").strip().lower()


def _response_context_sources(payload: dict[str, Any]) -> list[str]:
    response_mode = payload.get("response_mode")
    if not isinstance(response_mode, dict):
        response_mode = {}
    raw_sources = response_mode.get("context_sources")
    if not isinstance(raw_sources, list):
        raw_sources = response_mode.get("grounding_sources")
    if not isinstance(raw_sources, list):
        raw_sources = []

    context_sources: list[str] = []
    for source in raw_sources:
        normalized = _normalized_context_source(source)
        if normalized and normalized not in context_sources:
            context_sources.append(normalized)

    if not context_sources:
        grounding_mode = _normalized_context_source(response_mode.get("grounding_mode"))
        if grounding_mode in {"whiteboard", "recent_chat", "pending_whiteboard"}:
            context_sources.append(grounding_mode)
    return context_sources


def _normalized_context_source(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "working_memory":
        return "recall"
    if normalized in {"recall", "whiteboard", "recent_chat", "pending_whiteboard"}:
        return normalized
    return ""


def _answer_context_sources(
    *,
    memory_items: list[dict[str, Any]],
    protocol_items: list[dict[str, Any]],
    whiteboard_sources: list[str],
    has_recent_chat: bool,
) -> list[str]:
    sources: list[str] = []
    if memory_items:
        sources.append("memory")
    if protocol_items:
        sources.append("protocol")
    for source in whiteboard_sources:
        if source not in sources:
            sources.append(source)
    if has_recent_chat:
        sources.append("recent_chat")
    return sources


def _answer_evidence_sources(
    *,
    memory_items: list[dict[str, Any]],
    whiteboard_sources: list[str],
    has_recent_chat: bool,
) -> list[str]:
    sources: list[str] = []
    if memory_items:
        sources.append("memory")
    for source in whiteboard_sources:
        if source not in sources:
            sources.append(source)
    if has_recent_chat:
        sources.append("recent_chat")
    return sources


def _answer_basis_kind_and_label(
    *,
    source_buckets: list[str],
    memory_count: int,
    protocol_count: int,
    whiteboard_count: int,
    has_recent_chat: bool,
) -> tuple[str, str]:
    if len(source_buckets) >= 2:
        return "mixed_context", "Mixed Context"
    if memory_count > 0:
        return "memory_backed", "Memory-Backed"
    if protocol_count > 0:
        return "protocol_guided", "Protocol-Guided"
    if whiteboard_count > 0:
        return "whiteboard_grounded", "Whiteboard-Grounded"
    if has_recent_chat:
        return "recent_chat", "Recent Chat"
    return "intuitive", "Intuitive Answer"


def _answer_basis_summary(
    kind: str,
    *,
    memory_count: int,
    protocol_count: int,
    whiteboard_sources: list[str],
    has_recent_chat: bool,
    has_factual_grounding: bool,
) -> str:
    if kind == "intuitive":
        return "Answered from general model capability without specific Vantage context."
    if kind == "memory_backed":
        return f"Supported by {_plural(memory_count, 'recalled memory item')}."
    if kind == "protocol_guided":
        return f"Guided by {_plural(protocol_count, 'protocol item')}; protocols are guidance, not factual evidence."
    if kind == "whiteboard_grounded":
        if whiteboard_sources == ["pending_whiteboard"]:
            return "Supported by prior whiteboard context."
        return "Supported by whiteboard context."
    if kind == "recent_chat":
        return "Supported by recent chat context."
    if kind == "mixed_context":
        if has_factual_grounding:
            return "Supported by multiple context sources."
        return "Guided by multiple context sources without factual grounding."
    if has_recent_chat:
        return "Supported by recent chat context."
    return "Supported by available context."


def _plural(count: int, noun: str) -> str:
    suffix = "" if count == 1 else "s"
    return f"{count} {noun}{suffix}"
