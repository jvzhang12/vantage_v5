from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ROLE_NAMES = (
    "answer_context",
    "recall_context",
    "surface_to_open",
    "protocol_guidance",
    "pinned_or_continuity_context",
)
EXCERPT_LIMIT = 320
SUMMARY_LIMIT = 220
CONTEXT_HANDOFF_SCHEMA = "attention_recall_context_handoff.v1"
ROLE_PROJECTION_SCHEMA = "attention_recall_role_projection.v1"


@dataclass(frozen=True)
class ContextHandoffResource:
    id: str
    resource_id: str
    kind: str
    type: str | None
    title: str
    label: str | None
    roles: tuple[str, ...]
    origins: tuple[str, ...]
    flags: dict[str, bool]
    summary: str | None
    excerpt: str | None
    sent_to_response_llm: bool | None
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "kind": self.kind,
            "type": self.type,
            "title": self.title,
            "label": self.label,
            "roles": list(self.roles),
            "origins": list(self.origins),
            "flags": dict(self.flags),
            "summary": self.summary,
            "excerpt": self.excerpt,
            "sent_to_response_llm": self.sent_to_response_llm,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class AttentionRecallContextHandoff:
    """Internal read model for selected context across Attention, Recall, and Working Memory.

    The handoff is an observability/read-model contract only. It is built from
    finalized request/response fields and does not alter retrieval, generation,
    routing, UI actions, or writes.
    """

    resources: tuple[ContextHandoffResource, ...]
    roles: dict[str, list[dict[str, Any]]]
    comparison: dict[str, list[str]]
    notes: tuple[str, ...]

    def to_trace_payload(self) -> dict[str, Any]:
        return {
            "schema": CONTEXT_HANDOFF_SCHEMA,
            "roles": self.roles,
            "resources": [resource.to_dict() for resource in self.resources],
            "comparison": self.comparison,
            "notes": list(self.notes),
        }

    def to_role_projection_payload(self) -> dict[str, Any]:
        return {
            "schema": ROLE_PROJECTION_SCHEMA,
            "roles": self.roles,
            "resources": [resource.to_dict() for resource in self.resources],
            "comparison": self.comparison,
            "notes": [
                "Trace-only projection; ChatService.search_context and response generation are unchanged.",
                "Excerpts are compact debugging summaries, not hidden reasoning.",
            ],
        }


def build_attention_recall_context_handoff(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> AttentionRecallContextHandoff:
    """Build the internal context handoff from already-finalized turn payloads."""

    sent_to_llm = sent_to_response_llm(response_payload)
    resources: dict[str, dict[str, Any]] = {}
    selected_ids: list[str] = []
    visible_ids: list[str] = []
    pinned_ids: list[str] = []
    recall_ids: list[str] = []
    memory_trace_aliases: dict[str, str] = {}

    def safe_memory_trace_resource_id(item: dict[str, Any]) -> str | None:
        if not is_memory_trace_resource(item):
            return None
        raw_id = resource_id_from_item(item)
        alias = memory_trace_aliases.get(raw_id)
        if alias is None:
            alias = f"memory_trace:prior-turn-{len(memory_trace_aliases) + 1}"
            memory_trace_aliases[raw_id] = alias
        return alias

    for item in list_of_dicts(response_payload.get("selected_attention_resources")):
        resource = compact_resource(
            item,
            roles=["answer_context"],
            origins=["attention_selection"],
            selected=True,
            sent_to_response_llm=sent_to_llm,
            safe_resource_id=safe_memory_trace_resource_id(item),
        )
        merge_resource(resources, resource)
        selected_ids.append(resource["resource_id"])

    for item in list_of_dicts(response_payload.get("visible_artifacts")):
        resource = compact_resource(
            item,
            roles=["answer_context"],
            origins=["current_visible_context"],
            visible=True,
            sent_to_response_llm=sent_to_llm,
            safe_resource_id=safe_memory_trace_resource_id(item),
        )
        merge_resource(resources, resource)
        visible_ids.append(resource["resource_id"])

    for item in list_of_dicts(response_payload.get("recall") or response_payload.get("working_memory")):
        roles = ["answer_context", "recall_context"]
        origins = ["recall_search_context"]
        if is_protocol_resource(item):
            roles.append("protocol_guidance")
            origins.append("protocol_guidance")
        resource = compact_resource(
            item,
            roles=roles,
            origins=origins,
            sent_to_response_llm=sent_to_llm,
            safe_resource_id=safe_memory_trace_resource_id(item),
        )
        merge_resource(resources, resource)
        recall_ids.append(resource["resource_id"])

    pinned_context = response_payload.get("pinned_context") or response_payload.get("selected_record")
    if isinstance(pinned_context, dict):
        resource = compact_resource(
            pinned_context,
            roles=["pinned_or_continuity_context", "answer_context"],
            origins=["pinned_continuity"],
            pinned=True,
            sent_to_response_llm=sent_to_llm,
            safe_resource_id=safe_memory_trace_resource_id(pinned_context),
        )
        merge_resource(resources, resource)
        pinned_ids.append(resource["resource_id"])
    elif request_payload.get("pinned_context_id"):
        resource = compact_resource(
            {
                "id": request_payload.get("pinned_context_id"),
                "resource_id": request_payload.get("pinned_context_id"),
                "title": request_payload.get("pinned_context_id"),
            },
            roles=["pinned_or_continuity_context"],
            origins=["pinned_continuity"],
            pinned=True,
            sent_to_response_llm=None,
        )
        merge_resource(resources, resource)
        pinned_ids.append(resource["resource_id"])

    observed_context_ids = set(resources)
    for item in surface_open_resources(response_payload):
        safe_resource_id = safe_memory_trace_resource_id(item)
        resource_id = safe_resource_id or resource_id_from_item(item)
        resource = compact_resource(
            item,
            roles=["surface_to_open"],
            origins=["navigator_surface_open"],
            sent_to_response_llm=sent_to_llm if resource_id in observed_context_ids else None,
            safe_resource_id=safe_resource_id,
        )
        merge_resource(resources, resource)

    ordered_resource_dicts = list(resources.values())
    resource_models = tuple(_resource_model(resource) for resource in ordered_resource_dicts)
    roles = {
        role: [
            role_reference(resource)
            for resource in ordered_resource_dicts
            if role in resource.get("roles", [])
        ]
        for role in ROLE_NAMES
    }
    selected_set = set(selected_ids)
    recall_set = set(recall_ids)
    return AttentionRecallContextHandoff(
        resources=resource_models,
        roles=roles,
        comparison={
            "selected_attention_resource_ids": unique(selected_ids),
            "visible_resource_ids": unique(visible_ids),
            "pinned_resource_ids": unique(pinned_ids),
            "recall_resource_ids": unique(recall_ids),
            "selected_recall_overlap_ids": unique([item for item in selected_ids if item in recall_set]),
            "selected_attention_not_in_recall_ids": unique([item for item in selected_ids if item not in recall_set]),
            "recall_not_in_selected_attention_ids": unique([item for item in recall_ids if item not in selected_set]),
        },
        notes=(
            "Internal read model; ChatService.search_context and response generation are unchanged.",
            "Excerpts are compact grounding summaries, not hidden reasoning.",
        ),
    )


def compact_resource(
    item: dict[str, Any],
    *,
    roles: list[str],
    origins: list[str],
    selected: bool = False,
    visible: bool = False,
    pinned: bool = False,
    sent_to_response_llm: bool | None = None,
    safe_resource_id: str | None = None,
) -> dict[str, Any]:
    resource_id = safe_resource_id or resource_id_from_item(item, visible=visible)
    source_status = item.get("source_status") if isinstance(item.get("source_status"), dict) else {}
    memory_trace = is_memory_trace_resource(item)
    kind = "memory_trace" if memory_trace else (clean_optional(item.get("kind") or item.get("type")) or "resource")
    title = (
        memory_trace_public_title(item)
        if memory_trace
        else clean_optional(item.get("title") or item.get("label") or resource_id)
    )
    label = "Prior turn trace" if memory_trace else clean_optional(item.get("label"))
    summary = (
        "Prior turn context selected by Recall."
        if memory_trace
        else short_text(item.get("summary") or item.get("card"), limit=SUMMARY_LIMIT)
    )
    excerpt = None if memory_trace else short_text(item.get("excerpt") or item.get("content") or item.get("body"), limit=EXCERPT_LIMIT)
    provenance = (
        memory_trace_provenance(item, source_status)
        if memory_trace
        else {
            "source": clean_optional(item.get("source")),
            "source_label": clean_optional(item.get("source_label")),
            "scope": clean_optional(item.get("scope")),
            "durability": clean_optional(item.get("durability")),
            "is_canonical": item.get("is_canonical") if isinstance(item.get("is_canonical"), bool) else None,
            "source_status": {
                key: source_status.get(key)
                for key in ("store", "read_only", "writable")
                if key in source_status
            },
        }
    )
    return {
        "id": resource_id if memory_trace else clean_optional(item.get("id")) or resource_id,
        "resource_id": resource_id,
        "kind": kind,
        "type": clean_optional(item.get("type")),
        "title": title or resource_id,
        "label": label,
        "roles": unique(roles),
        "origins": unique(origins),
        "flags": {
            "selected": selected,
            "visible": visible,
            "pinned": pinned,
        },
        "summary": summary,
        "excerpt": excerpt,
        "sent_to_response_llm": sent_to_response_llm,
        "provenance": {key: value for key, value in provenance.items() if value not in (None, "", {})},
    }


def merge_resource(resources: dict[str, dict[str, Any]], incoming: dict[str, Any]) -> None:
    key = incoming["resource_id"]
    existing = resources.get(key)
    if existing is None:
        resources[key] = incoming
        return
    existing["roles"] = unique([*existing.get("roles", []), *incoming.get("roles", [])])
    existing["origins"] = unique([*existing.get("origins", []), *incoming.get("origins", [])])
    existing_flags = existing.get("flags") if isinstance(existing.get("flags"), dict) else {}
    incoming_flags = incoming.get("flags") if isinstance(incoming.get("flags"), dict) else {}
    existing["flags"] = {
        "selected": bool(existing_flags.get("selected") or incoming_flags.get("selected")),
        "visible": bool(existing_flags.get("visible") or incoming_flags.get("visible")),
        "pinned": bool(existing_flags.get("pinned") or incoming_flags.get("pinned")),
    }
    if not existing.get("summary") and incoming.get("summary"):
        existing["summary"] = incoming["summary"]
    if not existing.get("excerpt") and incoming.get("excerpt"):
        existing["excerpt"] = incoming["excerpt"]
    if existing.get("sent_to_response_llm") is None:
        existing["sent_to_response_llm"] = incoming.get("sent_to_response_llm")


def surface_open_resources(response_payload: dict[str, Any]) -> list[dict[str, Any]]:
    surface_invocation = response_payload.get("surface_invocation") if isinstance(response_payload.get("surface_invocation"), dict) else {}
    navigator_selection = response_payload.get("navigator_selection") if isinstance(response_payload.get("navigator_selection"), dict) else {}
    surface_to_open = clean_optional(navigator_selection.get("surface_to_open"))
    write_behavior = clean_optional(surface_invocation.get("write_behavior"))
    primary_surface = clean_optional(surface_invocation.get("primary_surface"))
    if not surface_to_open and not (primary_surface and write_behavior == "open_only"):
        return []
    primary_resource_id = clean_optional(
        navigator_selection.get("primary_resource_id")
        or surface_invocation.get("primary_resource_id")
        or surface_invocation.get("target_resource_id")
    )
    selected = list_of_dicts(response_payload.get("selected_attention_resources"))
    if primary_resource_id:
        normalized_target = normalize_resource_id(primary_resource_id)
        for item in selected:
            if normalize_resource_id(resource_id_from_item(item)) == normalized_target:
                return [item]
        return [
            {
                "id": primary_resource_id,
                "resource_id": primary_resource_id,
                "kind": surface_to_open or primary_surface or "surface",
                "title": primary_resource_id,
            }
        ]
    return selected[:1]


def role_reference(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource_id": resource.get("resource_id"),
        "kind": resource.get("kind"),
        "title": resource.get("title"),
        "origins": resource.get("origins") or [],
        "sent_to_response_llm": resource.get("sent_to_response_llm"),
    }


def resource_id_from_item(item: dict[str, Any], *, visible: bool = False) -> str:
    raw = item.get("resource_id") or item.get("id") or item.get("record_id") or item.get("concept_id")
    text = str(raw or "").strip()
    if visible and text and ":" not in text:
        return f"visible:{text}"
    if text:
        return text
    title = clean_optional(item.get("title") or item.get("label")) or "resource"
    return title


def is_protocol_resource(item: dict[str, Any]) -> bool:
    values = {
        str(item.get("kind") or "").strip().lower(),
        str(item.get("type") or "").strip().lower(),
        str(item.get("source") or "").strip().lower(),
        str(item.get("memory_role") or "").strip().lower(),
    }
    return "protocol" in values or str(item.get("id") or "").endswith("-protocol")


def is_memory_trace_resource(item: dict[str, Any]) -> bool:
    values = {
        str(item.get("kind") or "").strip().lower(),
        str(item.get("type") or "").strip().lower(),
        str(item.get("source") or "").strip().lower(),
        str(item.get("memory_role") or "").strip().lower(),
        str(item.get("source_tier") or "").strip().lower(),
    }
    identifier = str(item.get("id") or item.get("resource_id") or "").strip().lower()
    return "memory_trace" in values or identifier.startswith("memory_trace:")


def memory_trace_public_title(item: dict[str, Any]) -> str:
    identifier = clean_optional(item.get("id") or item.get("resource_id"))
    if identifier:
        return "Prior turn trace"
    return "Memory trace"


def memory_trace_provenance(item: dict[str, Any], source_status: dict[str, Any]) -> dict[str, Any]:
    provenance: dict[str, Any] = {"source": "memory_trace"}
    scope = clean_optional(item.get("scope"))
    if scope:
        provenance["scope"] = scope
    durability = clean_optional(item.get("durability"))
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


def sent_to_response_llm(response_payload: dict[str, Any]) -> bool | None:
    mode = str(response_payload.get("mode") or "").strip().lower()
    if mode in {"chat", "openai", "codex_oauth", "scenario_lab"}:
        return True
    if mode in {"fallback", "local_action", "clarification"}:
        return False
    if mode:
        return None
    return None


def list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def short_text(value: Any, *, limit: int) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def clean_optional(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


def normalize_resource_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("candidate-"):
        return text.removeprefix("candidate-")
    return text


def _resource_model(resource: dict[str, Any]) -> ContextHandoffResource:
    return ContextHandoffResource(
        id=str(resource.get("id") or resource.get("resource_id") or "resource"),
        resource_id=str(resource.get("resource_id") or resource.get("id") or "resource"),
        kind=str(resource.get("kind") or "resource"),
        type=clean_optional(resource.get("type")),
        title=str(resource.get("title") or resource.get("resource_id") or "resource"),
        label=clean_optional(resource.get("label")),
        roles=tuple(str(role) for role in resource.get("roles", []) if str(role or "").strip()),
        origins=tuple(str(origin) for origin in resource.get("origins", []) if str(origin or "").strip()),
        flags=resource.get("flags") if isinstance(resource.get("flags"), dict) else {},
        summary=clean_optional(resource.get("summary")),
        excerpt=clean_optional(resource.get("excerpt")),
        sent_to_response_llm=(
            resource.get("sent_to_response_llm")
            if isinstance(resource.get("sent_to_response_llm"), bool)
            else None
        ),
        provenance=resource.get("provenance") if isinstance(resource.get("provenance"), dict) else {},
    )
