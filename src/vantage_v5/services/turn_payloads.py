from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vantage_v5.services.context_budget import build_context_budget_payload
from vantage_v5.services.learned_review import ensure_write_review
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.response_mode import build_answer_basis_payload
from vantage_v5.services.turn_staging import StageAuditResult
from vantage_v5.services.turn_staging import StageProgressEvent
from vantage_v5.services.turn_staging import TurnStage
from vantage_v5.services.turn_staging import payload_for_audit
from vantage_v5.services.turn_staging import payload_for_progress
from vantage_v5.services.turn_staging import payload_for_stage
from vantage_v5.storage.workspaces import WorkspaceDocument


CONTENT_UNSET = object()
WHITEBOARD_TYPE_TO_STATUS = {
    "offer_whiteboard": "offered",
    "draft_whiteboard": "draft_ready",
}
WHITEBOARD_STATUS_TO_TYPE = {status: kind for kind, status in WHITEBOARD_TYPE_TO_STATUS.items()}


@dataclass(frozen=True, slots=True)
class LocalTurnBodyParts:
    assistant_message: str
    mode: str
    graph_action: dict[str, Any] | None = None
    created_record: dict[str, Any] | None = None
    workspace_update: dict[str, Any] | None = None
    turn_stage: TurnStage | dict[str, Any] | None = None
    stage_progress: StageProgressEvent | dict[str, Any] | list[dict[str, Any]] | None = None
    stage_audit: StageAuditResult | dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TurnResultParts:
    user_message: str
    history: list[dict[str, str]]
    workspace: WorkspaceDocument
    workspace_scope: str
    runtime_scope: str
    transient_workspace: bool
    semantic_frame: dict[str, Any]
    semantic_policy: dict[str, Any]
    pinned_context_id: str | None
    pinned_context: dict[str, Any] | None
    experiment: dict[str, Any]
    turn_body: LocalTurnBodyParts
    turn_interpretation: TurnInterpretationParts | dict[str, Any] | None = None
    turn_stage: TurnStage | dict[str, Any] | None = None
    stage_progress: StageProgressEvent | dict[str, Any] | list[dict[str, Any]] | None = None
    stage_audit: StageAuditResult | dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class LocalTurnContext:
    user_message: str
    history: list[dict[str, str]]
    workspace: WorkspaceDocument
    workspace_scope: str
    runtime_scope: str
    transient_workspace: bool
    semantic_frame: dict[str, Any]
    semantic_policy: dict[str, Any]
    pinned_context_id: str | None
    pinned_context: dict[str, Any] | None
    experiment: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ScenarioLabFallbackParts:
    turn_body: ChatTurnBodyParts | ScenarioLabTurnBodyParts
    navigation: dict[str, Any]
    comparison_question: str | None
    reason: str
    error_type: str
    error_message: str
    pinned_context_id: str | None
    pinned_context: dict[str, Any] | None
    turn_interpretation: TurnInterpretationParts | dict[str, Any]
    semantic_frame: dict[str, Any]
    semantic_policy: dict[str, Any]
    workspace: WorkspaceDocument
    runtime_scope: str
    workspace_scope: str
    transient_workspace: bool
    experiment: dict[str, Any]
    turn_stage: TurnStage | dict[str, Any] | None = None
    stage_progress: StageProgressEvent | dict[str, Any] | list[dict[str, Any]] | None = None
    stage_audit: StageAuditResult | dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ServiceTurnPayloadParts:
    turn_body: ChatTurnBodyParts | ScenarioLabTurnBodyParts
    pinned_context_id: str | None
    pinned_context: dict[str, Any] | None
    turn_interpretation: TurnInterpretationParts | dict[str, Any]
    semantic_frame: dict[str, Any]
    semantic_policy: dict[str, Any]
    workspace: WorkspaceDocument
    runtime_scope: str
    workspace_scope: str
    transient_workspace: bool
    experiment: dict[str, Any]
    turn_stage: TurnStage | dict[str, Any] | None = None
    stage_progress: StageProgressEvent | dict[str, Any] | list[dict[str, Any]] | None = None
    stage_audit: StageAuditResult | dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ChatTurnBodyParts:
    user_message: str
    assistant_message: str
    workspace_id: str
    workspace_title: str
    workspace_content: str | None
    workspace_update: dict[str, Any] | None
    concept_cards: list[dict[str, Any]]
    trace_notes: list[dict[str, Any]]
    saved_notes: list[dict[str, Any]]
    vault_notes: list[dict[str, Any]]
    candidate_concepts: list[dict[str, Any]]
    candidate_trace_notes: list[dict[str, Any]]
    candidate_saved_notes: list[dict[str, Any]]
    candidate_vault_notes: list[dict[str, Any]]
    candidate_memory: list[dict[str, Any]]
    working_memory: list[dict[str, Any]]
    recall_details: list[dict[str, Any]]
    learned: list[dict[str, Any]]
    memory_trace_record: dict[str, Any] | None
    response_mode: dict[str, Any]
    vetting: dict[str, Any]
    mode: str
    meta_action: dict[str, Any] | None
    graph_action: dict[str, Any] | None
    created_record: dict[str, Any] | None
    turn_stage: TurnStage | dict[str, Any] | None = None
    stage_progress: StageProgressEvent | dict[str, Any] | list[dict[str, Any]] | None = None
    stage_audit: StageAuditResult | dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ScenarioLabTurnBodyParts:
    user_message: str
    assistant_message: str
    workspace_id: str
    workspace_title: str
    workspace_content: str | None
    concept_cards: list[dict[str, Any]]
    saved_notes: list[dict[str, Any]]
    vault_notes: list[dict[str, Any]]
    candidate_concepts: list[dict[str, Any]]
    candidate_saved_notes: list[dict[str, Any]]
    candidate_vault_notes: list[dict[str, Any]]
    candidate_memory: list[dict[str, Any]]
    working_memory: list[dict[str, Any]]
    learned: list[dict[str, Any]]
    memory_trace_record: dict[str, Any] | None
    response_mode: dict[str, Any]
    vetting: dict[str, Any]
    navigator: dict[str, Any]
    comparison_question: str
    branches: list[dict[str, Any]]
    comparison_artifact: dict[str, Any]
    created_record: dict[str, Any] | None
    turn_stage: TurnStage | dict[str, Any] | None = None
    stage_progress: StageProgressEvent | dict[str, Any] | list[dict[str, Any]] | None = None
    stage_audit: StageAuditResult | dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TurnInterpretationParts:
    navigation: NavigationDecision
    requested_whiteboard_mode: str | None
    resolved_whiteboard_mode: str
    whiteboard_entry_mode: str | None
    explicit_whiteboard_draft_request: bool


def assemble_turn_interpretation_payload(parts: TurnInterpretationParts) -> dict[str, Any]:
    requested_mode = _normalized_requested_whiteboard_mode(parts.requested_whiteboard_mode)
    preserve_pinned_context = parts.navigation.preserve_pinned_context
    if preserve_pinned_context is None:
        preserve_pinned_context = parts.navigation.preserve_selected_record
    pinned_context_reason = parts.navigation.pinned_context_reason
    if pinned_context_reason is None:
        pinned_context_reason = parts.navigation.selected_record_reason
    return {
        "mode": parts.navigation.mode,
        "confidence": parts.navigation.confidence,
        "reason": parts.navigation.reason,
        "requested_whiteboard_mode": requested_mode,
        "resolved_whiteboard_mode": parts.resolved_whiteboard_mode if parts.navigation.mode == "chat" else None,
        "whiteboard_mode_source": _whiteboard_mode_source(
            requested_mode,
            parts.navigation,
            parts.resolved_whiteboard_mode,
            explicit_whiteboard_draft_request=parts.explicit_whiteboard_draft_request,
        ),
        "whiteboard_entry_mode": parts.whiteboard_entry_mode,
        "preserve_pinned_context": preserve_pinned_context,
        "pinned_context_reason": pinned_context_reason,
        "preserve_selected_record": preserve_pinned_context,
        "selected_record_reason": pinned_context_reason,
        "control_panel": parts.navigation.control_panel or {},
    }


def _turn_interpretation_payload(value: TurnInterpretationParts | dict[str, Any] | None) -> dict[str, Any] | None:
    if isinstance(value, TurnInterpretationParts):
        return assemble_turn_interpretation_payload(value)
    if isinstance(value, dict):
        return value
    return None


def build_local_turn_parts(
    context: LocalTurnContext,
    *,
    turn_body: LocalTurnBodyParts,
    workspace: WorkspaceDocument | None = None,
    transient_workspace: bool | None = None,
    turn_interpretation: TurnInterpretationParts | dict[str, Any] | None = None,
    turn_stage: TurnStage | dict[str, Any] | None = None,
    stage_progress: StageProgressEvent | dict[str, Any] | list[dict[str, Any]] | None = None,
    stage_audit: StageAuditResult | dict[str, Any] | None = None,
) -> TurnResultParts:
    return TurnResultParts(
        user_message=context.user_message,
        history=context.history,
        workspace=workspace or context.workspace,
        workspace_scope=context.workspace_scope,
        runtime_scope=context.runtime_scope,
        transient_workspace=context.transient_workspace if transient_workspace is None else transient_workspace,
        semantic_frame=context.semantic_frame,
        semantic_policy=context.semantic_policy,
        pinned_context_id=context.pinned_context_id,
        pinned_context=context.pinned_context,
        experiment=context.experiment,
        turn_body=turn_body,
        turn_interpretation=turn_interpretation,
        turn_stage=turn_stage,
        stage_progress=stage_progress,
        stage_audit=stage_audit,
    )


def assemble_local_turn_payload(
    parts: TurnResultParts,
) -> dict[str, Any]:
    response_mode = _response_mode_payload(
        workspace_has_context=parts.workspace_scope != "excluded" and bool(parts.workspace.content.strip()),
        history_has_context=bool(parts.history),
        pending_workspace_has_context=False,
    )
    empty_memory = _memory_payload([], [])
    payload = finalize_turn_payload(
        {
            "user_message": parts.user_message,
            "assistant_message": parts.turn_body.assistant_message,
            "workspace": assemble_workspace_payload_for_turn(
                None,
                workspace=parts.workspace,
                scope=parts.runtime_scope,
                context_scope=parts.workspace_scope,
                transient_workspace=parts.transient_workspace,
            ),
            "workspace_update": parts.turn_body.workspace_update,
            "memory": empty_memory,
            "selected_memory": empty_memory,
            "candidate_memory": empty_memory,
            "concept_cards": [],
            "saved_notes": [],
            "vault_notes": [],
            "turn_vault_notes": [],
            "candidate_concepts": [],
            "trace_notes": [],
            "candidate_trace_notes": [],
            "candidate_saved_notes": [],
            "candidate_vault_notes": [],
            "candidate_memory_results": [],
            "recall": [],
            "working_memory": [],
            "recall_details": [],
            "learned": [parts.turn_body.created_record] if parts.turn_body.created_record else [],
            "memory_trace_record": None,
            "response_mode": response_mode,
            "vetting": {"rationale": parts.semantic_policy.get("reason") or "Handled by semantic policy.", "selected_ids": []},
            "mode": parts.turn_body.mode,
            "meta_action": {"action": "no_op", "rationale": "Handled by semantic policy."},
            "graph_action": parts.turn_body.graph_action,
            "created_record": parts.turn_body.created_record,
            "turn_interpretation": _turn_interpretation_payload(parts.turn_interpretation),
            "semantic_frame": parts.semantic_frame,
            "semantic_policy": parts.semantic_policy,
            "experiment": parts.experiment,
            "turn_stage": parts.turn_stage or parts.turn_body.turn_stage,
            "stage_progress": parts.stage_progress or parts.turn_body.stage_progress,
            "stage_audit": parts.stage_audit or parts.turn_body.stage_audit,
        },
        pinned_context_id=parts.pinned_context_id,
        pinned_context=parts.pinned_context,
    )
    return attach_safe_turn_state(payload)


def assemble_service_turn_payload(
    parts: ServiceTurnPayloadParts,
) -> dict[str, Any]:
    payload = finalize_turn_payload(
        _assemble_turn_body_payload(parts.turn_body),
        pinned_context_id=parts.pinned_context_id,
        pinned_context=parts.pinned_context,
    )
    payload["turn_interpretation"] = _turn_interpretation_payload(parts.turn_interpretation)
    payload["semantic_frame"] = parts.semantic_frame
    payload["semantic_policy"] = parts.semantic_policy
    payload["workspace"] = assemble_workspace_payload_for_turn(
        payload.get("workspace"),
        workspace=parts.workspace,
        scope=parts.runtime_scope,
        context_scope=parts.workspace_scope,
        transient_workspace=parts.transient_workspace,
    )
    payload["experiment"] = parts.experiment
    payload["turn_stage"] = parts.turn_stage or payload.get("turn_stage")
    payload["stage_progress"] = parts.stage_progress or payload.get("stage_progress")
    payload["stage_audit"] = parts.stage_audit or payload.get("stage_audit")
    payload["context_budget"] = build_context_budget_payload(payload)
    _preserve_stage_payloads(payload)
    return attach_safe_turn_state(payload)


def assemble_chat_turn_body(parts: ChatTurnBodyParts) -> dict[str, Any]:
    learned = _record_list(parts.learned)
    created_record = parts.created_record if isinstance(parts.created_record, dict) else (learned[0] if learned else None)
    for record in learned:
        ensure_write_review(record)
    if created_record is not None:
        ensure_write_review(created_record)
    selected_memory = _turn_memory_payload(parts.saved_notes, parts.vault_notes)
    candidate_memory = _turn_memory_payload(parts.candidate_saved_notes, parts.candidate_vault_notes)
    payload = {
        "user_message": parts.user_message,
        "assistant_message": parts.assistant_message,
        "workspace": {
            "workspace_id": parts.workspace_id,
            "title": parts.workspace_title,
            "content": parts.workspace_content,
        },
        "workspace_update": parts.workspace_update,
        "memory": selected_memory,
        "selected_memory": selected_memory,
        "candidate_memory": candidate_memory,
        "concept_cards": parts.concept_cards,
        "saved_notes": parts.saved_notes,
        "vault_notes": parts.vault_notes,
        "turn_vault_notes": parts.vault_notes,
        "candidate_concepts": parts.candidate_concepts,
        "trace_notes": parts.trace_notes,
        "candidate_trace_notes": parts.candidate_trace_notes,
        "candidate_saved_notes": parts.candidate_saved_notes,
        "candidate_vault_notes": parts.candidate_vault_notes,
        "candidate_memory_results": parts.candidate_memory,
        "recall": parts.working_memory,
        "working_memory": parts.working_memory,
        "recall_details": parts.recall_details,
        "learned": learned,
        "memory_trace_record": parts.memory_trace_record,
        "response_mode": parts.response_mode,
        "vetting": parts.vetting,
        "mode": parts.mode,
        "meta_action": parts.meta_action,
        "graph_action": parts.graph_action,
        "created_record": created_record,
        "turn_stage": parts.turn_stage,
        "stage_progress": parts.stage_progress or [],
        "stage_audit": parts.stage_audit,
    }
    payload["answer_basis"] = build_answer_basis_payload(payload)
    return payload


def assemble_scenario_lab_turn_body(parts: ScenarioLabTurnBodyParts) -> dict[str, Any]:
    learned = _record_list(parts.learned)
    created_record = parts.created_record if isinstance(parts.created_record, dict) else (learned[0] if learned else None)
    for record in learned:
        ensure_write_review(record)
    if created_record is not None:
        ensure_write_review(created_record)
    selected_memory = _turn_memory_payload(parts.saved_notes, parts.vault_notes)
    candidate_memory = _turn_memory_payload(parts.candidate_saved_notes, parts.candidate_vault_notes)
    payload = {
        "user_message": parts.user_message,
        "assistant_message": parts.assistant_message,
        "workspace": {
            "workspace_id": parts.workspace_id,
            "title": parts.workspace_title,
            "content": parts.workspace_content,
        },
        "memory": selected_memory,
        "selected_memory": selected_memory,
        "candidate_memory": candidate_memory,
        "concept_cards": parts.concept_cards,
        "saved_notes": parts.saved_notes,
        "vault_notes": parts.vault_notes,
        "turn_vault_notes": parts.vault_notes,
        "candidate_concepts": parts.candidate_concepts,
        "candidate_saved_notes": parts.candidate_saved_notes,
        "candidate_vault_notes": parts.candidate_vault_notes,
        "candidate_memory_results": parts.candidate_memory,
        "recall": parts.working_memory,
        "working_memory": parts.working_memory,
        "learned": learned,
        "memory_trace_record": parts.memory_trace_record,
        "response_mode": parts.response_mode,
        "vetting": parts.vetting,
        "mode": "scenario_lab",
        "meta_action": {
            "action": "no_op",
            "rationale": "Scenario Lab writes branch workspaces and a comparison artifact outside the normal memory loop.",
        },
        "graph_action": None,
        "created_record": created_record,
        "turn_stage": parts.turn_stage,
        "stage_progress": parts.stage_progress or [],
        "stage_audit": parts.stage_audit,
        "scenario_lab": {
            "navigator": parts.navigator,
            "question": parts.comparison_question,
            "comparison_question": parts.comparison_question,
            "summary": parts.comparison_artifact.get("card") or parts.assistant_message,
            "recommendation": parts.comparison_artifact.get("recommendation"),
            "branches": parts.branches,
            "comparison_artifact": parts.comparison_artifact,
        },
    }
    payload["answer_basis"] = build_answer_basis_payload(payload)
    return payload


def assemble_scenario_lab_fallback_payload(
    parts: ScenarioLabFallbackParts,
) -> dict[str, Any]:
    payload = finalize_turn_payload(
        _assemble_turn_body_payload(parts.turn_body),
        pinned_context_id=parts.pinned_context_id,
        pinned_context=parts.pinned_context,
    )
    scenario_lab_error = {
        "status": "failed",
        "navigation": parts.navigation,
        "pinned_context_id": parts.pinned_context_id,
        "pinned_context": parts.pinned_context,
        "selected_record_id": parts.pinned_context_id,
        "selected_record": parts.pinned_context,
        "comparison_question": parts.comparison_question,
        "reason": parts.reason,
        "error": {
            "type": parts.error_type,
            "message": parts.error_message,
        },
        "fallback_mode": "chat",
        "chat_turn_mode": payload.get("mode"),
    }
    payload["scenario_lab"] = scenario_lab_error
    payload["scenario_lab_error"] = scenario_lab_error["error"]
    payload["turn_interpretation"] = _turn_interpretation_payload(parts.turn_interpretation)
    payload["semantic_frame"] = parts.semantic_frame
    payload["semantic_policy"] = parts.semantic_policy
    payload["workspace"] = assemble_workspace_payload_for_turn(
        payload.get("workspace"),
        workspace=parts.workspace,
        scope=parts.runtime_scope,
        context_scope=parts.workspace_scope,
        transient_workspace=parts.transient_workspace,
    )
    payload["experiment"] = parts.experiment
    payload["turn_stage"] = parts.turn_stage or payload.get("turn_stage")
    payload["stage_progress"] = parts.stage_progress or payload.get("stage_progress")
    payload["stage_audit"] = parts.stage_audit or payload.get("stage_audit")
    payload["context_budget"] = build_context_budget_payload(payload)
    _preserve_stage_payloads(payload)
    return attach_safe_turn_state(payload)


def _assemble_turn_body_payload(
    turn_body: ChatTurnBodyParts | ScenarioLabTurnBodyParts,
) -> dict[str, Any]:
    if isinstance(turn_body, ChatTurnBodyParts):
        return assemble_chat_turn_body(turn_body)
    if isinstance(turn_body, ScenarioLabTurnBodyParts):
        return assemble_scenario_lab_turn_body(turn_body)
    raise TypeError(f"Unsupported turn body parts: {type(turn_body).__name__}")


def assemble_workspace_payload_for_turn(
    workspace_payload: dict[str, Any] | None,
    *,
    workspace: WorkspaceDocument,
    scope: str,
    context_scope: str,
    transient_workspace: bool,
) -> dict[str, Any]:
    existing_payload = workspace_payload if isinstance(workspace_payload, dict) else {}
    if "content" in existing_payload:
        content = existing_payload.get("content")
        if transient_workspace and content is None:
            content = workspace.content
    else:
        content = workspace.content if transient_workspace else None
    merged_payload = {
        **existing_payload,
        **_workspace_payload(workspace, scope=scope, content_override=content),
    }
    merged_payload["context_scope"] = context_scope
    return merged_payload


def finalize_turn_payload(
    payload: dict[str, Any],
    *,
    pinned_context_id: str | None,
    pinned_context: dict[str, Any] | None,
) -> dict[str, Any]:
    learned = _record_list(payload.get("learned"))
    payload["learned"] = learned
    created_record = payload.get("created_record")
    if not isinstance(created_record, dict):
        created_record = None
        payload["created_record"] = None
    if created_record is None and learned:
        created_record = learned[0]
        payload["created_record"] = created_record
    elif created_record is not None and not learned:
        learned = [created_record]
        payload["learned"] = learned
    for record in learned:
        ensure_write_review(record)
    if created_record is not None:
        ensure_write_review(created_record)

    graph_action = payload.get("graph_action")
    if isinstance(graph_action, dict):
        record_id = graph_action.get("record_id")
        concept_id = graph_action.get("concept_id")
        if record_id is None and concept_id is not None:
            graph_action["record_id"] = concept_id
        if concept_id is None and record_id is not None:
            graph_action["concept_id"] = record_id

    workspace_update = payload.get("workspace_update")
    if isinstance(workspace_update, dict):
        workspace_type = str(workspace_update.get("type") or "").strip() or None
        workspace_status = str(workspace_update.get("status") or "").strip() or None
        if workspace_status is None and workspace_type is not None:
            workspace_status = WHITEBOARD_TYPE_TO_STATUS.get(workspace_type)
        if workspace_type is None and workspace_status is not None:
            workspace_type = WHITEBOARD_STATUS_TO_TYPE.get(workspace_status)
        if workspace_type is not None:
            workspace_update["type"] = workspace_type
        if workspace_status is not None:
            workspace_update["status"] = workspace_status

    recall = payload.get("recall")
    working_memory = payload.get("working_memory")
    if isinstance(recall, list) and not isinstance(working_memory, list):
        payload["working_memory"] = recall
    elif isinstance(working_memory, list) and not isinstance(recall, list):
        payload["recall"] = working_memory
    elif not isinstance(recall, list) and not isinstance(working_memory, list):
        payload["recall"] = []
        payload["working_memory"] = []

    payload["pinned_context_id"] = pinned_context_id
    payload["pinned_context"] = pinned_context
    payload["selected_record_id"] = pinned_context_id
    payload["selected_record"] = pinned_context
    _preserve_stage_payloads(payload)
    payload["answer_basis"] = build_answer_basis_payload(payload)
    payload["context_budget"] = build_context_budget_payload(payload)
    return payload


def _record_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _preserve_stage_payloads(payload: dict[str, Any]) -> None:
    for key, normalizer in (
        ("turn_stage", payload_for_stage),
        ("stage_progress", payload_for_progress),
        ("stage_audit", payload_for_audit),
    ):
        value = normalizer(payload.get(key))
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value


def attach_safe_turn_state(payload: dict[str, Any]) -> dict[str, Any]:
    payload["system_state"] = safe_system_state_payload(payload)
    payload["activity"] = safe_activity_payload(payload)
    return payload


def safe_system_state_payload(payload: dict[str, Any]) -> dict[str, Any]:
    workspace = payload.get("workspace") if isinstance(payload.get("workspace"), dict) else {}
    return {
        "mode": payload.get("mode"),
        "available_surfaces": ["chat", "draft", "inspect", "scenario_lab"],
        "available_controls": [
            "respond",
            "recall",
            "apply_protocol",
            "open_whiteboard",
            "draft_whiteboard",
            "open_scenario_lab",
            "inspect_context",
            "save_whiteboard",
            "publish_artifact",
            "manage_experiment",
            "ask_clarification",
        ],
        "user": {"id": payload.get("user_id")} if payload.get("user_id") else None,
        "experiment": payload.get("experiment"),
        "workspace": {
            "workspace_id": workspace.get("workspace_id"),
            "title": workspace.get("title"),
            "scope": workspace.get("scope"),
            "context_scope": workspace.get("context_scope"),
            "has_visible_content": bool(str(workspace.get("content") or "").strip()),
            "scenario_kind": workspace.get("scenario_kind"),
            "transient": bool(workspace.get("transient")),
        },
        "pinned_context": _safe_context_reference(payload.get("pinned_context")),
        "selected_record": _safe_context_reference(payload.get("selected_record")),
        "pending_workspace_update": _safe_pending_workspace_reference(payload.get("workspace_update")),
    }


def safe_activity_payload(payload: dict[str, Any]) -> dict[str, Any]:
    graph_action = payload.get("graph_action") if isinstance(payload.get("graph_action"), dict) else {}
    workspace_update = payload.get("workspace_update") if isinstance(payload.get("workspace_update"), dict) else {}
    scenario_lab = payload.get("scenario_lab") if isinstance(payload.get("scenario_lab"), dict) else {}
    response_mode = payload.get("response_mode") if isinstance(payload.get("response_mode"), dict) else {}
    answer_basis = payload.get("answer_basis") if isinstance(payload.get("answer_basis"), dict) else {}
    summary = (
        str(graph_action.get("summary") or "").strip()
        or str(workspace_update.get("summary") or "").strip()
        or str(scenario_lab.get("summary") or "").strip()
        or _single_line(payload.get("assistant_message") or "")[:180]
    )
    mode = _activity_kind(payload)
    recall_count = response_mode.get("recall_count", len(payload.get("working_memory") or []))
    context_summary = _activity_context_summary(answer_basis, recall_count=recall_count)
    steps = [
        {
            "id": "interpret",
            "label": "Interpreted request",
            "status": "completed",
            "summary": _single_line((payload.get("turn_interpretation") or {}).get("reason") or ""),
        },
        {
            "id": "context",
            "label": "Prepared context",
            "status": "completed",
            "summary": context_summary,
        },
    ]
    if mode == "scenario_lab":
        steps.append(
            {
                "id": "scenario_lab",
                "label": "Compared branches",
                "status": "failed" if scenario_lab.get("status") == "failed" else "completed",
                "summary": summary,
            }
        )
    elif workspace_update:
        steps.append(
            {
                "id": "draft",
                "label": "Prepared draft",
                "status": "completed",
                "summary": str(workspace_update.get("summary") or "").strip(),
            }
        )
    else:
        steps.append(
            {
                "id": "respond",
                "label": "Composed response",
                "status": "completed",
                "summary": summary,
            }
        )
    actions = [graph_action] if graph_action else []
    created_record_ids = [
        str(record.get("id"))
        for record in payload.get("learned") or []
        if isinstance(record, dict) and record.get("id")
    ]
    return {
        "mode": mode,
        "kind": mode,
        "status": "completed",
        "summary": summary,
        "steps": steps,
        "items": steps,
        "actions": actions,
        "created_record_ids": created_record_ids,
        "recall_count": recall_count,
        "learned_count": len(payload.get("learned") or []),
        "created_record_id": (payload.get("created_record") or {}).get("id")
        if isinstance(payload.get("created_record"), dict)
        else None,
        "graph_action_type": graph_action.get("type"),
        "workspace_update_status": workspace_update.get("status"),
    }


def _activity_context_summary(answer_basis: dict[str, Any], *, recall_count: Any) -> str:
    counts = answer_basis.get("counts") if isinstance(answer_basis.get("counts"), dict) else {}
    memory_count = counts.get("memory")
    protocol_count = counts.get("protocol")
    if not isinstance(memory_count, int):
        memory_count = int(memory_count) if str(memory_count or "").isdigit() else None
    if not isinstance(protocol_count, int):
        protocol_count = int(protocol_count) if str(protocol_count or "").isdigit() else 0
    if memory_count is None:
        memory_count = recall_count if isinstance(recall_count, int) else len(answer_basis.get("evidence_sources") or [])
    parts: list[str] = []
    if memory_count:
        parts.append(f"{memory_count} recalled memory item{'s' if memory_count != 1 else ''}")
    if protocol_count:
        parts.append(f"{protocol_count} protocol item{'s' if protocol_count != 1 else ''}")
    if parts:
        return f"{' and '.join(parts)} in scope."
    label = str(answer_basis.get("label") or "").strip()
    if label:
        return f"{label} basis prepared."
    normalized_recall_count = recall_count if isinstance(recall_count, int) else 0
    return f"{normalized_recall_count} recalled item(s) in scope."


def _activity_kind(payload: dict[str, Any]) -> str:
    mode = str(payload.get("mode") or "").strip()
    if mode == "scenario_lab":
        return "scenario_lab"
    if mode in {"local_action", "clarification"}:
        return mode
    if payload.get("workspace_update"):
        return "whiteboard"
    return "chat"


def _turn_memory_payload(
    saved_notes: list[dict[str, Any]],
    reference_notes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "saved_notes": saved_notes,
        "reference_notes": reference_notes,
        "total": len(saved_notes) + len(reference_notes),
    }


def _safe_context_reference(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "id": value.get("id") or value.get("record_id"),
        "title": value.get("title"),
        "type": value.get("type"),
        "source": value.get("source"),
    }


def _safe_pending_workspace_reference(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "status": value.get("status"),
        "type": value.get("type"),
        "workspace_id": value.get("workspace_id"),
        "title": value.get("title"),
        "proposal_kind": value.get("proposal_kind"),
    }


def _single_line(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _memory_payload(saved_notes: list[dict[str, Any]], reference_notes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "saved_notes": saved_notes,
        "reference_notes": reference_notes,
        "counts": {
            "saved_notes": len(saved_notes),
            "reference_notes": len(reference_notes),
            "total": len(saved_notes) + len(reference_notes),
        },
    }


def _response_mode_payload(
    *,
    workspace_has_context: bool,
    history_has_context: bool,
    pending_workspace_has_context: bool,
) -> dict[str, Any]:
    context_sources: list[str] = []
    if workspace_has_context:
        context_sources.append("whiteboard")
    if history_has_context:
        context_sources.append("recent_chat")
    if pending_workspace_has_context:
        context_sources.append("pending_whiteboard")
    if not context_sources:
        grounding_mode = "ungrounded"
    elif len(context_sources) == 1:
        grounding_mode = context_sources[0]
    else:
        grounding_mode = "mixed_context"
    return {
        "kind": "grounded" if context_sources else "best_guess",
        "grounding_mode": grounding_mode,
        "context_sources": context_sources,
        "grounding_sources": context_sources,
        "legacy_context_sources": ["working_memory" if source == "recall" else source for source in context_sources],
        "recall_count": 0,
        "has_workspace_context": workspace_has_context,
        "has_history_context": history_has_context,
        "has_pending_workspace_context": pending_workspace_has_context,
    }


def _workspace_payload(
    document: WorkspaceDocument,
    *,
    scope: str,
    content_override: str | None | object = CONTENT_UNSET,
) -> dict[str, Any]:
    content = document.content if content_override is CONTENT_UNSET else content_override
    return {
        "workspace_id": document.workspace_id,
        "title": document.title,
        "content": content,
        "scope": scope,
        **_scenario_payload(document.scenario_metadata),
    }


def _scenario_payload(metadata: dict[str, Any] | None) -> dict[str, Any]:
    cleaned_metadata = _clean_scenario_metadata(metadata)
    return {
        "scenario_kind": cleaned_metadata.get("scenario_kind") if cleaned_metadata else None,
        "scenario": cleaned_metadata,
    }


def _clean_scenario_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_value = _clean_scenario_metadata_value(value)
        if normalized_value in (None, "", [], {}):
            continue
        cleaned[key] = normalized_value
    return cleaned or None


def _clean_scenario_metadata_value(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            normalized = _clean_scenario_metadata_value(item)
            if normalized in (None, "", [], {}):
                continue
            cleaned[str(key).strip()] = normalized
        return cleaned
    if isinstance(value, list):
        cleaned_list: list[Any] = []
        for item in value:
            normalized = _clean_scenario_metadata_value(item)
            if normalized in (None, "", [], {}):
                continue
            cleaned_list.append(normalized)
        return cleaned_list
    normalized_value = str(value).strip()
    return normalized_value or None


def _normalized_requested_whiteboard_mode(value: str | None) -> str:
    if value in {"chat", "offer", "draft", "auto"}:
        return value
    return "auto"


def _whiteboard_mode_source(
    requested_whiteboard_mode: str,
    navigation: NavigationDecision,
    resolved_whiteboard_mode: str,
    *,
    explicit_whiteboard_draft_request: bool,
) -> str | None:
    if navigation.mode != "chat":
        return None
    if requested_whiteboard_mode == "chat":
        return "composer"
    if explicit_whiteboard_draft_request and resolved_whiteboard_mode == "draft":
        return "request"
    if requested_whiteboard_mode in {"offer", "draft"}:
        return "composer"
    if navigation.whiteboard_mode in {"chat", "offer", "draft", "auto"}:
        return "interpreter"
    if resolved_whiteboard_mode == "auto":
        return "default"
    return None
