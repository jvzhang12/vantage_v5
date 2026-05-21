from __future__ import annotations

import re
from typing import Any


PUBLIC_CURRENT_TRACE_ID = "current-turn"
PUBLIC_PRIOR_TRACE_PREFIX = "memory_trace:prior-turn"
PUBLIC_PRIOR_TRACE_TITLE = "Prior turn trace"
PUBLIC_PRIOR_TRACE_SUMMARY = "Prior turn context selected by Recall."
MEMORY_TRACE_PUBLIC_BODY_MARKERS = (
    "## Source Turn",
    "## User Message",
    "## Assistant Response",
)
PROMPT_DERIVED_TURN_ID_RE = re.compile(r"^(?:[a-z_]+:)?turn-\d{8,}(?:[-:].*)?$", re.IGNORECASE)
NORMAL_RECORD_VALUES = {
    "artifact",
    "concept",
    "draft",
    "memory",
    "note",
    "protocol",
    "reference_note",
    "saved_note",
    "vault_note",
    "whiteboard",
}


def sanitize_public_attention_state_payload(value: dict[str, Any] | None) -> dict[str, Any]:
    """Return browser-safe Attention state without changing selection authority."""

    if not isinstance(value, dict):
        return {
            "query_frame": None,
            "attention_candidates": [],
            "navigator_selection": None,
            "selected_attention_resources": [],
        }
    payload = dict(value)
    payload["attention_candidates"] = public_memory_trace_list(payload.get("attention_candidates"))
    payload["navigator_selection"] = public_attention_selection(payload.get("navigator_selection"))
    payload["selected_attention_resources"] = public_memory_trace_list(payload.get("selected_attention_resources"))
    return payload


def public_memory_trace_record(
    value: dict[str, Any] | None,
    *,
    recalled_ids: list[str] | None = None,
    learned_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if not is_memory_trace_derived(value):
        return dict(value)
    payload = {
        "id": PUBLIC_CURRENT_TRACE_ID,
        "resource_id": PUBLIC_CURRENT_TRACE_ID,
        "title": "Current turn trace",
        "type": "memory_trace",
        "card": "Current turn context was logged.",
        "status": value.get("status"),
        "kind": "memory_trace",
        "memory_role": "turn_continuity",
        "recall_status": "logged",
        "source_tier": "recent",
        "source": "memory_trace",
        "source_label": "Memory Trace",
        "scope": value.get("scope"),
        "trace_kind": optional_public_text(value.get("trace_kind")),
        "turn_mode": optional_public_text(value.get("turn_mode")),
        "trace_scope": optional_public_text(value.get("trace_scope")),
        "workspace_id": optional_public_text(value.get("workspace_id")),
        "workspace_scope": optional_public_text(value.get("workspace_scope")),
        "whiteboard_in_scope": value.get("whiteboard_in_scope")
        if isinstance(value.get("whiteboard_in_scope"), bool)
        else None,
        "grounding_mode": optional_public_text(value.get("grounding_mode")),
        "context_sources": public_text_list(value.get("context_sources")),
        "recall_count": optional_public_int(value.get("recall_count")),
        "working_memory_count": optional_public_int(value.get("working_memory_count")),
        "history_count": optional_public_int(value.get("history_count")),
        "learned_count": optional_public_int(value.get("learned_count")),
        "recalled_ids": recalled_ids if recalled_ids is not None else public_safe_id_list(value.get("recalled_ids")),
        "recalled_sources": public_text_list(value.get("recalled_sources")),
        "learned_ids": learned_ids if learned_ids is not None else public_safe_id_list(value.get("learned_ids")),
        "learned_sources": public_text_list(value.get("learned_sources")),
        "pending_workspace_status": optional_public_text(value.get("pending_workspace_status")),
        "preserved_context_id": public_safe_id(
            value.get("preserved_context_id"),
            fallback_alias=prior_turn_alias(1),
        ),
        "preserved_context_source": optional_public_text(value.get("preserved_context_source")),
    }
    return compact_public_dict(payload)


def public_memory_trace_list(values: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    sanitized: list[dict[str, Any]] = []
    trace_index = 0
    for item in values:
        if not isinstance(item, dict):
            continue
        if is_memory_trace_derived(item):
            trace_index += 1
            sanitized.append(public_memory_trace_item(item, alias=prior_turn_alias(trace_index)))
        else:
            sanitized.append(dict(item))
    return sanitized


def public_memory_trace_item(value: dict[str, Any], *, alias: str) -> dict[str, Any]:
    reason = public_memory_trace_reason(value)
    payload = {
        "id": alias,
        "resource_id": alias,
        "title": PUBLIC_PRIOR_TRACE_TITLE,
        "label": PUBLIC_PRIOR_TRACE_TITLE,
        "type": "memory_trace",
        "card": PUBLIC_PRIOR_TRACE_SUMMARY,
        "summary": PUBLIC_PRIOR_TRACE_SUMMARY,
        "kind": "memory_trace",
        "memory_role": value.get("memory_role") or "turn_continuity",
        "recall_status": value.get("recall_status") or "candidate",
        "source_tier": value.get("source_tier") or "recent",
        "score": value.get("score"),
        "reason": "memory_trace: public_safe_alias",
        "source": "memory_trace",
        "source_label": "Memory Trace",
        "scope": value.get("scope"),
        "durability": value.get("durability"),
        "is_canonical": value.get("is_canonical") if isinstance(value.get("is_canonical"), bool) else None,
        "trust": value.get("trust"),
        "recall_reason": reason,
        "why_recalled": reason,
        "app": value.get("app") if value.get("app") not in (None, "") else None,
        "source_status": public_source_status(value.get("source_status")),
        "timestamps": public_timestamps(value.get("timestamps")),
        "suggested_surface": value.get("suggested_surface"),
        "why_selected": "Prior Memory Trace context selected for this turn."
        if value.get("why_selected")
        else None,
        "data": public_memory_trace_data(value.get("data")),
    }
    return compact_public_dict(payload)


def public_attention_selection(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    payload = dict(value)
    for key in ("selected_ids", "supporting_resource_ids", "rejected_candidate_ids"):
        if key in payload:
            payload[key] = public_safe_id_list(payload.get(key))
    if "primary_resource_id" in payload:
        payload["primary_resource_id"] = public_safe_id(
            payload.get("primary_resource_id"),
            fallback_alias=prior_turn_alias(1),
        )
    surface_to_open = payload.get("surface_to_open")
    if isinstance(surface_to_open, dict):
        safe_surface = dict(surface_to_open)
        for key in ("id", "resource_id"):
            if key in safe_surface:
                safe_surface[key] = public_safe_id(safe_surface.get(key), fallback_alias=prior_turn_alias(1))
        payload["surface_to_open"] = safe_surface
    return payload


def public_turn_interpretation_dict(value: dict[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    if "attention_selection" in payload:
        payload["attention_selection"] = public_attention_selection(payload.get("attention_selection"))
    return payload


def public_vetting_payload(value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    payload = dict(value)
    if "selected_ids" in payload:
        payload["selected_ids"] = public_safe_id_list(payload.get("selected_ids"))
    return payload


def public_turn_id(value: Any, *, trace_id: str | None) -> str | None:
    turn_id = optional_public_text(value)
    if turn_id is None:
        return optional_public_text(trace_id)
    if is_prompt_derived_id(turn_id):
        return optional_public_text(trace_id)
    return turn_id


def public_turn_trace_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    if optional_public_text(value.get("id")) is None:
        return None
    return PUBLIC_CURRENT_TRACE_ID


def public_safe_id_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    safe: list[str] = []
    trace_index = 0
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        if is_prompt_derived_id(text):
            trace_index += 1
            safe.append(prior_turn_alias(trace_index))
        else:
            safe.append(text)
    return safe


def public_safe_id(value: Any, *, fallback_alias: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if is_prompt_derived_id(text):
        return fallback_alias
    return text


def prior_turn_alias(index: int) -> str:
    return f"{PUBLIC_PRIOR_TRACE_PREFIX}-{index}"


def is_memory_trace_derived(value: dict[str, Any]) -> bool:
    values = {
        str(value.get("kind") or "").strip().lower(),
        str(value.get("type") or "").strip().lower(),
        str(value.get("source") or "").strip().lower(),
        str(value.get("memory_role") or "").strip().lower(),
        str(value.get("source_tier") or "").strip().lower(),
        str(value.get("app") or "").strip().lower(),
    }
    identifier = str(value.get("id") or value.get("resource_id") or "").strip().lower()
    if "memory_trace" in values or identifier.startswith("memory_trace:") or has_memory_trace_source_body(value):
        return True
    if values & NORMAL_RECORD_VALUES:
        return False
    # With no trustworthy kind/source, a storage-shaped turn id is treated as a
    # public-safety signal. Natural slugs such as "turn-taking-in-dialogue" are
    # not prompt-derived ids.
    return is_prompt_derived_id(identifier)


def is_prompt_derived_id(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text or text == PUBLIC_CURRENT_TRACE_ID:
        return False
    if text.startswith(PUBLIC_PRIOR_TRACE_PREFIX):
        return False
    return (
        text.startswith("memory_trace:")
        or bool(PROMPT_DERIVED_TURN_ID_RE.match(text))
        or bool(re.search(r":turn-\d{8,}", text))
    )


def has_memory_trace_source_body(value: dict[str, Any]) -> bool:
    text = "\n".join(
        str(value.get(key) or "")
        for key in ("body", "content", "excerpt", "summary", "card", "title")
        if value.get(key) is not None
    )
    if any(marker in text for marker in MEMORY_TRACE_PUBLIC_BODY_MARKERS):
        return True
    title = str(value.get("title") or "").strip().lower()
    return title.startswith("turn trace:")


def public_memory_trace_reason(value: dict[str, Any]) -> str:
    existing = str(value.get("recall_reason") or value.get("why_recalled") or "").strip()
    if existing and not is_prompt_derived_id(existing) and "## " not in existing:
        return existing
    return "Prior Memory Trace context selected by Recall."


def public_memory_trace_title(value: dict[str, Any] | None = None) -> str:
    return PUBLIC_PRIOR_TRACE_TITLE if value is not None else "Memory trace"


def public_memory_trace_provenance(value: dict[str, Any], source_status: dict[str, Any]) -> dict[str, Any]:
    provenance: dict[str, Any] = {"source": "memory_trace"}
    scope = optional_public_text(value.get("scope"))
    if scope:
        provenance["scope"] = scope
    durability = optional_public_text(value.get("durability"))
    if durability:
        provenance["durability"] = durability
    compact_status = {
        key: source_status.get(key)
        for key in ("store", "read_only", "writable")
        if key in source_status
    }
    if compact_status:
        provenance["source_status"] = compact_status
    return provenance


def public_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for text in (optional_public_text(item) for item in value) if text]


def optional_public_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def optional_public_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def public_source_status(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        key: value.get(key)
        for key in ("store", "trust", "read_only", "writable")
        if key in value and value.get(key) not in (None, "", {}, [])
    }


def public_timestamps(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        key: value.get(key)
        for key in ("file_modified_at", "file_created_at", "created_at", "updated_at")
        if key in value and value.get(key) not in (None, "", {}, [])
    }


def public_memory_trace_data(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        key: item
        for key, item in value.items()
        if key in {"trace_kind", "turn_mode", "trace_scope"} and item not in (None, "", {}, [])
    }


def compact_public_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item not in (None, "", [], {})}
