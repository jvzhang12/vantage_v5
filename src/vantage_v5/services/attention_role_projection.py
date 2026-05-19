from __future__ import annotations

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
WORKING_MEMORY_VIEW_VERSION = "working_memory_view.v1"


def build_attention_recall_role_projection(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build a trace-only role view over finalized context payloads.

    This intentionally observes the already-finalized response contract. It does
    not alter selection, recall, prompt context, routing, writes, or UI behavior.
    """

    sent_to_llm = _sent_to_response_llm(response_payload)
    resources: dict[str, dict[str, Any]] = {}
    selected_ids: list[str] = []
    visible_ids: list[str] = []
    pinned_ids: list[str] = []
    recall_ids: list[str] = []

    for item in _list_of_dicts(response_payload.get("selected_attention_resources")):
        resource = _compact_resource(
            item,
            roles=["answer_context"],
            origins=["attention_selection"],
            selected=True,
            sent_to_response_llm=sent_to_llm,
        )
        _merge_resource(resources, resource)
        selected_ids.append(resource["resource_id"])

    for item in _list_of_dicts(response_payload.get("visible_artifacts")):
        resource = _compact_resource(
            item,
            roles=["answer_context"],
            origins=["current_visible_context"],
            visible=True,
            sent_to_response_llm=sent_to_llm,
        )
        _merge_resource(resources, resource)
        visible_ids.append(resource["resource_id"])

    for item in _list_of_dicts(response_payload.get("recall") or response_payload.get("working_memory")):
        roles = ["answer_context", "recall_context"]
        origins = ["recall_search_context"]
        if _is_protocol_resource(item):
            roles.append("protocol_guidance")
            origins.append("protocol_guidance")
        resource = _compact_resource(
            item,
            roles=roles,
            origins=origins,
            sent_to_response_llm=sent_to_llm,
        )
        _merge_resource(resources, resource)
        recall_ids.append(resource["resource_id"])

    pinned_context = response_payload.get("pinned_context") or response_payload.get("selected_record")
    if isinstance(pinned_context, dict):
        resource = _compact_resource(
            pinned_context,
            roles=["pinned_or_continuity_context", "answer_context"],
            origins=["pinned_continuity"],
            pinned=True,
            sent_to_response_llm=sent_to_llm,
        )
        _merge_resource(resources, resource)
        pinned_ids.append(resource["resource_id"])
    elif request_payload.get("pinned_context_id"):
        resource = _compact_resource(
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
        _merge_resource(resources, resource)
        pinned_ids.append(resource["resource_id"])

    for item in _surface_open_resources(response_payload):
        resource = _compact_resource(
            item,
            roles=["surface_to_open"],
            origins=["navigator_surface_open"],
            sent_to_response_llm=sent_to_llm,
        )
        _merge_resource(resources, resource)

    ordered_resources = list(resources.values())
    roles = {
        role: [
            _role_reference(resource)
            for resource in ordered_resources
            if role in resource.get("roles", [])
        ]
        for role in ROLE_NAMES
    }
    selected_set = set(selected_ids)
    recall_set = set(recall_ids)
    return {
        "schema": "attention_recall_role_projection.v1",
        "roles": roles,
        "resources": ordered_resources,
        "comparison": {
            "selected_attention_resource_ids": _unique(selected_ids),
            "visible_resource_ids": _unique(visible_ids),
            "pinned_resource_ids": _unique(pinned_ids),
            "recall_resource_ids": _unique(recall_ids),
            "selected_recall_overlap_ids": _unique([item for item in selected_ids if item in recall_set]),
            "selected_attention_not_in_recall_ids": _unique([item for item in selected_ids if item not in recall_set]),
            "recall_not_in_selected_attention_ids": _unique([item for item in recall_ids if item not in selected_set]),
        },
        "notes": [
            "Trace-only projection; ChatService.search_context and response generation are unchanged.",
            "Excerpts are compact debugging summaries, not hidden reasoning.",
        ],
    }


def build_working_memory_view_payload(
    *,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    role_projection: dict[str, Any] | None = None,
    turn_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the product-safe Working Memory view for the latest response.

    The view is a bounded public contract over already-finalized response
    fields. It reuses the Attention/Recall role projection as its source of
    truth and adds a compact execution summary from TurnPlan-compatible fields.
    It does not include raw prompts, full resource bodies, or hidden reasoning.
    """

    projection = (
        role_projection
        if isinstance(role_projection, dict)
        else build_attention_recall_role_projection(
            request_payload=request_payload,
            response_payload=response_payload,
        )
    )
    plan = turn_plan if isinstance(turn_plan, dict) else {}
    resources = [
        _working_memory_resource(resource, response_payload=response_payload)
        for resource in _list_of_dicts(projection.get("resources"))
    ]
    roles = {
        role: [
            _working_memory_role_reference(resource)
            for resource in resources
            if role in resource.get("roles", [])
        ]
        for role in ROLE_NAMES
    }
    trace_record = response_payload.get("memory_trace_record")
    trace_id = trace_record.get("id") if isinstance(trace_record, dict) else None
    turn_request = plan.get("request") if isinstance(plan.get("request"), dict) else {}
    return {
        "schema": WORKING_MEMORY_VIEW_VERSION,
        "turn": {
            "turn_id": _clean_optional(request_payload.get("turn_id") or turn_request.get("turn_id")),
            "trace_id": _clean_optional(trace_id),
            "response_mode": _clean_optional(_response_mode_kind(response_payload.get("response_mode"))),
            "mode": _clean_optional(response_payload.get("mode")),
        },
        "roles": roles,
        "resources": resources,
        "comparison": _compact_projection_comparison(projection.get("comparison")),
        "execution_summary": _working_memory_execution_summary(
            response_payload=response_payload,
            turn_plan=plan,
        ),
        "source": {
            "attention_recall_role_projection_schema": _clean_optional(projection.get("schema")),
            "turn_plan_version": _clean_optional(plan.get("version")),
        },
        "notes": [
            "Shows bounded grounding/context/provenance and execution decisions for the latest response.",
            "Does not include hidden reasoning, chain-of-thought, raw prompts, or full resource bodies.",
        ],
    }


def _compact_resource(
    item: dict[str, Any],
    *,
    roles: list[str],
    origins: list[str],
    selected: bool = False,
    visible: bool = False,
    pinned: bool = False,
    sent_to_response_llm: bool | None = None,
) -> dict[str, Any]:
    resource_id = _resource_id(item, visible=visible)
    source_status = item.get("source_status") if isinstance(item.get("source_status"), dict) else {}
    provenance = {
        "source": _clean_optional(item.get("source")),
        "source_label": _clean_optional(item.get("source_label")),
        "scope": _clean_optional(item.get("scope")),
        "durability": _clean_optional(item.get("durability")),
        "is_canonical": item.get("is_canonical") if isinstance(item.get("is_canonical"), bool) else None,
        "source_status": {
            key: source_status.get(key)
            for key in ("store", "read_only", "writable")
            if key in source_status
        },
    }
    return {
        "id": _clean_optional(item.get("id")) or resource_id,
        "resource_id": resource_id,
        "kind": _clean_optional(item.get("kind") or item.get("type")) or "resource",
        "type": _clean_optional(item.get("type")),
        "title": _clean_optional(item.get("title") or item.get("label") or resource_id),
        "label": _clean_optional(item.get("label")),
        "roles": _unique(roles),
        "origins": _unique(origins),
        "flags": {
            "selected": selected,
            "visible": visible,
            "pinned": pinned,
        },
        "summary": _short_text(item.get("summary") or item.get("card"), limit=SUMMARY_LIMIT),
        "excerpt": _short_text(item.get("excerpt") or item.get("content") or item.get("body"), limit=EXCERPT_LIMIT),
        "sent_to_response_llm": sent_to_response_llm,
        "provenance": {key: value for key, value in provenance.items() if value not in (None, "", {})},
    }


def _working_memory_resource(
    resource: dict[str, Any],
    *,
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    roles = _unique([str(role) for role in resource.get("roles", []) if str(role or "").strip()])
    origins = _unique([str(origin) for origin in resource.get("origins", []) if str(origin or "").strip()])
    resource_id = _clean_optional(resource.get("resource_id")) or _clean_optional(resource.get("id")) or "resource"
    compact = {
        "id": _clean_optional(resource.get("id")) or resource_id,
        "resource_id": resource_id,
        "kind": _clean_optional(resource.get("kind")),
        "type": _clean_optional(resource.get("type")),
        "title": _clean_optional(resource.get("title")),
        "label": _clean_optional(resource.get("label")),
        "roles": roles,
        "origins": origins,
        "flags": _compact_flags(resource.get("flags")),
        "summary": _short_text(resource.get("summary"), limit=SUMMARY_LIMIT),
        "excerpt": _short_text(resource.get("excerpt"), limit=EXCERPT_LIMIT),
        "sent_to_response_llm": resource.get("sent_to_response_llm")
        if isinstance(resource.get("sent_to_response_llm"), bool)
        else None,
        "provenance": _compact_provenance(resource.get("provenance")),
        "influence": {
            "answer_generation": "answer_context" in roles,
            "ui_surface_action": "surface_to_open" in roles,
            "write_or_proposal_decision": _resource_influenced_write_or_proposal(resource_id, response_payload),
        },
    }
    return {key: value for key, value in compact.items() if value not in (None, "", {}, [])}


def _working_memory_role_reference(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource_id": resource.get("resource_id"),
        "kind": resource.get("kind"),
        "title": resource.get("title"),
        "origins": resource.get("origins") or [],
        "sent_to_response_llm": resource.get("sent_to_response_llm"),
    }


def _working_memory_execution_summary(
    *,
    response_payload: dict[str, Any],
    turn_plan: dict[str, Any],
) -> dict[str, Any]:
    ui_surface_action = turn_plan.get("ui_surface_action") if isinstance(turn_plan.get("ui_surface_action"), dict) else {}
    write_ledger = turn_plan.get("write_ledger") if isinstance(turn_plan.get("write_ledger"), dict) else {}
    write_projection = turn_plan.get("write_projection") if isinstance(turn_plan.get("write_projection"), dict) else {}
    graph_action = response_payload.get("graph_action") if isinstance(response_payload.get("graph_action"), dict) else None
    created_record = response_payload.get("created_record") if isinstance(response_payload.get("created_record"), dict) else None
    artifact_actions = _list_of_dicts(response_payload.get("artifact_actions"))
    return {
        "surface": {
            "mode": _clean_optional(ui_surface_action.get("mode")),
            "surface": _clean_optional(ui_surface_action.get("surface")),
            "target_resource_id": _clean_optional(ui_surface_action.get("target_resource_id")),
            "target_resource_kind": _clean_optional(ui_surface_action.get("target_resource_kind")),
            "authority": _clean_optional(ui_surface_action.get("authority")),
            "active_surface_id": _clean_optional(response_payload.get("active_surface_id")),
            "surface_payload_count": len(_list_of_dicts(response_payload.get("surface_payloads"))),
        },
        "writes": {
            "categories": list(write_ledger.get("categories") or ["none"]),
            "intended_write_kind": _clean_optional(write_projection.get("intended_write_kind")),
            "effect_agreement": _clean_optional(write_projection.get("effect_agreement")),
            "workspace_update_type": _workspace_update_type(response_payload.get("workspace_update")),
            "graph_action_type": _clean_optional(graph_action.get("type") if graph_action else None),
            "created_record": _compact_created_record(created_record),
            "artifact_action_count": len(artifact_actions),
            "proposal_count": sum(1 for action in artifact_actions if _is_proposed_artifact_action(action)),
        },
    }


def _compact_flags(value: Any) -> dict[str, bool]:
    flags = value if isinstance(value, dict) else {}
    return {
        "selected": bool(flags.get("selected")),
        "visible": bool(flags.get("visible")),
        "pinned": bool(flags.get("pinned")),
    }


def _compact_provenance(value: Any) -> dict[str, Any]:
    provenance = value if isinstance(value, dict) else {}
    compact: dict[str, Any] = {}
    for key in ("source", "source_label", "scope", "durability", "is_canonical"):
        item = provenance.get(key)
        if item not in (None, "", {}):
            compact[key] = item
    source_status = provenance.get("source_status")
    if isinstance(source_status, dict):
        compact_status = {
            key: source_status.get(key)
            for key in ("store", "read_only", "writable")
            if key in source_status
        }
        if compact_status:
            compact["source_status"] = compact_status
    return compact


def _compact_projection_comparison(value: Any) -> dict[str, list[str]]:
    comparison = value if isinstance(value, dict) else {}
    keys = (
        "selected_attention_resource_ids",
        "visible_resource_ids",
        "pinned_resource_ids",
        "recall_resource_ids",
        "selected_recall_overlap_ids",
        "selected_attention_not_in_recall_ids",
        "recall_not_in_selected_attention_ids",
    )
    return {
        key: _unique([str(item) for item in comparison.get(key, [])])
        if isinstance(comparison.get(key), list)
        else []
        for key in keys
    }


def _resource_influenced_write_or_proposal(resource_id: str, response_payload: dict[str, Any]) -> bool | None:
    target_ids = _write_or_proposal_target_ids(response_payload)
    if not target_ids:
        return None
    return _normalize_resource_id(resource_id) in target_ids


def _write_or_proposal_target_ids(response_payload: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    graph_action = response_payload.get("graph_action")
    if isinstance(graph_action, dict):
        for key in ("record_id", "concept_id", "artifact_id", "memory_id", "target_id"):
            value = _clean_optional(graph_action.get(key))
            if value:
                ids.add(_normalize_resource_id(value))
    created_record = response_payload.get("created_record")
    if isinstance(created_record, dict):
        for key in ("resource_id", "id", "record_id", "concept_id"):
            value = _clean_optional(created_record.get(key))
            if value:
                ids.add(_normalize_resource_id(value))
    for action in _list_of_dicts(response_payload.get("artifact_actions")):
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        for candidate in (action, payload):
            for key in ("id", "resource_id", "target_id", "artifact_id", "task_id", "event_id"):
                value = _clean_optional(candidate.get(key))
                if value:
                    ids.add(_normalize_resource_id(value))
    return ids


def _workspace_update_type(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    return _clean_optional(value.get("type") or value.get("status") or value.get("proposal_kind"))


def _compact_created_record(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    compact = {
        "id": _clean_optional(value.get("id") or value.get("record_id") or value.get("concept_id")),
        "kind": _clean_optional(value.get("kind") or value.get("type")),
        "type": _clean_optional(value.get("type")),
        "title": _clean_optional(value.get("title")),
    }
    return {key: item for key, item in compact.items() if item not in (None, "", {}, [])}


def _is_proposed_artifact_action(action: dict[str, Any]) -> bool:
    payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
    return str(action.get("status") or payload.get("status") or "").strip().lower() == "proposed"


def _response_mode_kind(value: Any) -> str | None:
    if isinstance(value, dict):
        return _clean_optional(value.get("kind") or value.get("mode"))
    return _clean_optional(value)


def _merge_resource(resources: dict[str, dict[str, Any]], incoming: dict[str, Any]) -> None:
    key = incoming["resource_id"]
    existing = resources.get(key)
    if existing is None:
        resources[key] = incoming
        return
    existing["roles"] = _unique([*existing.get("roles", []), *incoming.get("roles", [])])
    existing["origins"] = _unique([*existing.get("origins", []), *incoming.get("origins", [])])
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


def _surface_open_resources(response_payload: dict[str, Any]) -> list[dict[str, Any]]:
    surface_invocation = response_payload.get("surface_invocation") if isinstance(response_payload.get("surface_invocation"), dict) else {}
    navigator_selection = response_payload.get("navigator_selection") if isinstance(response_payload.get("navigator_selection"), dict) else {}
    surface_to_open = _clean_optional(navigator_selection.get("surface_to_open"))
    write_behavior = _clean_optional(surface_invocation.get("write_behavior"))
    primary_surface = _clean_optional(surface_invocation.get("primary_surface"))
    if not surface_to_open and not (primary_surface and write_behavior == "open_only"):
        return []
    primary_resource_id = _clean_optional(
        navigator_selection.get("primary_resource_id")
        or surface_invocation.get("primary_resource_id")
        or surface_invocation.get("target_resource_id")
    )
    selected = _list_of_dicts(response_payload.get("selected_attention_resources"))
    if primary_resource_id:
        normalized_target = _normalize_resource_id(primary_resource_id)
        for item in selected:
            if _normalize_resource_id(_resource_id(item)) == normalized_target:
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


def _role_reference(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource_id": resource.get("resource_id"),
        "kind": resource.get("kind"),
        "title": resource.get("title"),
        "origins": resource.get("origins") or [],
        "sent_to_response_llm": resource.get("sent_to_response_llm"),
    }


def _resource_id(item: dict[str, Any], *, visible: bool = False) -> str:
    raw = item.get("resource_id") or item.get("id") or item.get("record_id") or item.get("concept_id")
    text = str(raw or "").strip()
    if visible and text and ":" not in text:
        return f"visible:{text}"
    if text:
        return text
    title = _clean_optional(item.get("title") or item.get("label")) or "resource"
    return title


def _is_protocol_resource(item: dict[str, Any]) -> bool:
    values = {
        str(item.get("kind") or "").strip().lower(),
        str(item.get("type") or "").strip().lower(),
        str(item.get("source") or "").strip().lower(),
        str(item.get("memory_role") or "").strip().lower(),
    }
    return "protocol" in values or str(item.get("id") or "").endswith("-protocol")


def _sent_to_response_llm(response_payload: dict[str, Any]) -> bool | None:
    mode = str(response_payload.get("mode") or "").strip().lower()
    if mode in {"chat", "openai", "codex_oauth", "scenario_lab"}:
        return True
    if mode in {"fallback", "local_action", "clarification"}:
        return False
    if mode:
        return None
    return None


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _short_text(value: Any, *, limit: int) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _clean_optional(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


def _normalize_resource_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("candidate-"):
        return text.removeprefix("candidate-")
    return text
