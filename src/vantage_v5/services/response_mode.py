from __future__ import annotations

from typing import Any

from vantage_v5.services.search import CandidateMemory

BEST_GUESS_PREFACE = "This is new to me, but my best guess is:"


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
