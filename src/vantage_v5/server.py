from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from vantage_v5.config import AppConfig
from vantage_v5.services.chat import ChatService
from vantage_v5.services.executor import GraphActionExecutor
from vantage_v5.services.meta import MetaService
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.navigator import NavigatorService
from vantage_v5.services.scenario_lab import ScenarioLabService
from vantage_v5.services.search import ConceptSearchService
from vantage_v5.services.vetting import ConceptVettingService
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.experiments import ExperimentSession
from vantage_v5.storage.experiments import ExperimentSessionManager
from vantage_v5.storage.memory_trace import MemoryTraceStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.state import ActiveWorkspaceStateStore
from vantage_v5.storage.vault import VaultNoteStore
from vantage_v5.storage.workspaces import WorkspaceDocument
from vantage_v5.storage.workspaces import WorkspaceStore


logger = logging.getLogger(__name__)
SCENARIO_LAB_MIN_CONFIDENCE = 0.68
EXPLICIT_WHITEBOARD_OPEN_RE = re.compile(
    r"\b(?:open|pull up|bring up|show|use|start|resume)\s+(?:the\s+)?whiteboard\b",
    re.IGNORECASE,
)
EXPLICIT_WHITEBOARD_DRAFT_RE = re.compile(
    r"\b(?:draft|write|put|move|build|plan|outline|sketch|work|create|review|refine|play)\b.{0,80}\b(?:in|on|into)\s+(?:the\s+)?whiteboard\b",
    re.IGNORECASE,
)
WHITEBOARD_EDIT_VERB_RE = re.compile(
    r"\b(?:update|revise|edit|refine|rewrite|change|adjust|add|remove|include|incorporate|personalize|polish|tighten|shorten|expand|improve)\b",
    re.IGNORECASE,
)
WHITEBOARD_EDIT_TARGET_RE = re.compile(
    r"\b(?:email|draft|whiteboard|plan|list|outline|essay|document|note|signature|greeting|it|this|that)\b",
    re.IGNORECASE,
)
PENDING_ACCEPT_RE = re.compile(
    r"\b(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\b",
    re.IGNORECASE,
)
PENDING_CONTINUE_RE = re.compile(
    r"\b(?:continue|keep going|go on|carry on|pick up where we left off|resume)\b",
    re.IGNORECASE,
)
PENDING_REFERENCE_RE = re.compile(
    r"\b(?:draft|whiteboard|email|plan|list|outline|document|note|it|this|that)\b",
    re.IGNORECASE,
)
PENDING_EDIT_TARGET_RE = re.compile(
    r"\b(?:email|draft|whiteboard|plan|list|outline|essay|document|note|it|this|that)\b",
    re.IGNORECASE,
)
MAX_PENDING_FOLLOW_UP_LENGTH = 240
WHITEBOARD_TYPE_TO_STATUS = {
    "offer_whiteboard": "offered",
    "draft_whiteboard": "draft_ready",
}
WHITEBOARD_STATUS_TO_TYPE = {status: kind for kind, status in WHITEBOARD_TYPE_TO_STATUS.items()}
CONTENT_UNSET = object()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)
    workspace_id: str | None = None
    workspace_scope: str = "auto"
    workspace_content: str | None = None
    whiteboard_mode: str = "auto"
    selected_record_id: str | None = None
    memory_intent: str = "auto"
    pending_workspace_update: dict[str, Any] | None = None


class WhiteboardAcceptRequest(BaseModel):
    history: list[dict[str, str]] = Field(default_factory=list)
    workspace_id: str | None = None
    workspace_scope: str = "auto"
    workspace_content: str | None = None
    selected_record_id: str | None = None
    memory_intent: str = "auto"
    pending_workspace_update: dict[str, Any]


class WorkspaceUpdateRequest(BaseModel):
    content: str
    workspace_id: str | None = None


class WorkspaceOpenRequest(BaseModel):
    workspace_id: str = Field(min_length=1)


class ConceptPromotionRequest(BaseModel):
    workspace_id: str | None = None
    title: str | None = None
    card: str | None = None
    content: str | None = None


class ConceptOpenRequest(BaseModel):
    record_id: str | None = None
    concept_id: str | None = None


class ExperimentStartRequest(BaseModel):
    seed_from_workspace: bool = False


def _serialize_concept_card(concept: Any, *, scope: str = "durable") -> dict[str, Any]:
    return {
        "id": concept.id,
        "title": concept.title,
        "type": concept.type,
        "card": concept.card,
        "body": concept.body,
        "status": concept.status,
        "links_to": concept.links_to,
        "comes_from": concept.comes_from,
        "source": "concept",
        "source_label": "Experiment concepts" if scope == "experiment" else "Concept KB",
        "trust": "high",
        "kind": "concept",
        "scope": scope,
        "filename": concept.path.name,
    }


def _serialize_saved_note_card(record: Any, *, scope: str = "durable") -> dict[str, Any]:
    source_label = {
        "memory": "Experiment memories" if scope == "experiment" else "Saved memories",
        "artifact": "Experiment artifacts" if scope == "experiment" else "Saved artifacts",
    }.get(record.source, "Saved notes")
    payload = {
        "id": record.id,
        "title": record.title,
        "type": record.type,
        "card": record.card,
        "body": record.body,
        "status": record.status,
        "links_to": record.links_to,
        "comes_from": record.comes_from,
        "source": record.source,
        "source_label": source_label,
        "trust": record.trust,
        "kind": "saved_note",
        "scope": scope,
        "filename": record.path.name,
    }
    payload.update(_scenario_payload(_saved_record_scenario_metadata(record)))
    return payload


def _serialize_vault_note_card(note: Any) -> dict[str, Any]:
    return {
        "id": note.id,
        "title": note.title,
        "type": note.type,
        "card": note.card,
        "body": note.body,
        "source": note.source,
        "source_label": "Reference notes",
        "trust": note.trust,
        "kind": "reference_note",
        "path": note.relative_path,
        "folder": note.folder,
        "tags": note.tags,
        "modified_at": note.modified_at,
    }


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


def _clean_scenario_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            normalized_list = [str(item).strip() for item in value if str(item).strip()]
            if normalized_list:
                cleaned[key] = normalized_list
            continue
        normalized_value = str(value).strip()
        if normalized_value:
            cleaned[key] = normalized_value
    return cleaned or None


def _scenario_payload(metadata: dict[str, Any] | None) -> dict[str, Any]:
    cleaned_metadata = _clean_scenario_metadata(metadata)
    return {
        "scenario_kind": cleaned_metadata.get("scenario_kind") if cleaned_metadata else None,
        "scenario": cleaned_metadata,
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


def _workspace_from_buffer(document: WorkspaceDocument, content: str) -> WorkspaceDocument:
    scenario_metadata = WorkspaceStore.parse_scenario_metadata(content, workspace_id=document.workspace_id)
    return WorkspaceDocument(
        workspace_id=document.workspace_id,
        title=WorkspaceStore._title_from_content(document.workspace_id, content),
        content=content,
        path=document.path,
        scenario_metadata=scenario_metadata or document.scenario_metadata,
    )


def _workspace_from_unsaved_buffer(workspace_store: WorkspaceStore, workspace_id: str, content: str) -> WorkspaceDocument:
    path = workspace_store.workspaces_dir / f"{workspace_id}.md"
    return WorkspaceDocument(
        workspace_id=workspace_id,
        title=WorkspaceStore._title_from_content(workspace_id, content),
        content=content,
        path=path,
        scenario_metadata=WorkspaceStore.parse_scenario_metadata(content, workspace_id=workspace_id),
    )


def _workspace_without_context(document: WorkspaceDocument) -> WorkspaceDocument:
    return WorkspaceDocument(
        workspace_id=document.workspace_id,
        title=document.title,
        content="",
        path=document.path,
        scenario_metadata=document.scenario_metadata,
    )


def _saved_record_scenario_metadata(record: Any) -> dict[str, Any] | None:
    if getattr(record, "source", None) != "artifact" and getattr(record, "type", None) != "scenario_comparison":
        return None
    return ArtifactStore.parse_scenario_metadata(record)


def _workspace_payload_for_turn(
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


def _finalize_turn_payload(
    payload: dict[str, Any],
    *,
    selected_record_id: str | None,
    selected_record: dict[str, Any] | None,
) -> dict[str, Any]:
    learned = payload.get("learned")
    if not isinstance(learned, list):
        learned = []
    created_record = payload.get("created_record")
    if created_record is None and learned:
        payload["created_record"] = learned[0]
    elif created_record is not None and not learned:
        payload["learned"] = [created_record]

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

    payload["selected_record_id"] = selected_record_id
    payload["selected_record"] = selected_record
    return payload


def create_app(config: AppConfig | None = None) -> FastAPI:
    cfg = config or AppConfig.from_env()
    repo_root = cfg.repo_root

    durable_concept_store = ConceptStore(repo_root / "concepts")
    durable_memory_store = MemoryStore(repo_root / "memories")
    durable_memory_trace_store = MemoryTraceStore(repo_root / "memory_trace")
    durable_artifact_store = ArtifactStore(repo_root / "artifacts")
    durable_workspace_store = WorkspaceStore(repo_root / "workspaces")
    durable_state_store = ActiveWorkspaceStateStore(repo_root / "state" / "active_workspace.json")
    experiment_manager = ExperimentSessionManager(repo_root / "state")
    vault_store = VaultNoteStore(
        vault_root=cfg.nexus_root,
        include_paths=cfg.nexus_include_paths,
        exclude_paths=cfg.nexus_exclude_paths,
    )
    search_service = ConceptSearchService()
    vetting_service = ConceptVettingService(
        model=cfg.model,
        openai_api_key=cfg.openai_api_key,
    )
    meta_service = MetaService(
        model=cfg.model,
        openai_api_key=cfg.openai_api_key,
    )
    navigator_service = NavigatorService(
        model=cfg.model,
        openai_api_key=cfg.openai_api_key,
    )

    app = FastAPI(title="Vantage V5", version="0.1.0")
    web_dir = Path(__file__).resolve().parent / "webapp"
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    def _session_info(session: ExperimentSession | None) -> dict[str, Any]:
        if session is None:
            return {"active": False, "session_id": None, "saved_note_count": 0}
        return {
            "active": True,
            "session_id": session.session_id,
            "saved_note_count": (
                len(MemoryStore(session.memories_dir).list_memories())
                + len(ArtifactStore(session.artifacts_dir).list_artifacts())
            ),
        }

    def _runtime(session: ExperimentSession | None) -> dict[str, Any]:
        if session is None:
            concept_store = durable_concept_store
            memory_store = durable_memory_store
            memory_trace_store = durable_memory_trace_store
            artifact_store = durable_artifact_store
            workspace_store = durable_workspace_store
            state_store = durable_state_store
            reference_concept_store = None
            reference_memory_store = None
            reference_memory_trace_store = None
            reference_artifact_store = None
            traces_dir = repo_root / "traces"
            scope = "durable"
        else:
            concept_store = ConceptStore(session.concepts_dir)
            memory_store = MemoryStore(session.memories_dir)
            memory_trace_store = MemoryTraceStore(session.memory_trace_dir)
            artifact_store = ArtifactStore(session.artifacts_dir)
            workspace_store = WorkspaceStore(session.workspaces_dir)
            state_store = ActiveWorkspaceStateStore(session.state_path)
            reference_concept_store = durable_concept_store
            reference_memory_store = durable_memory_store
            reference_memory_trace_store = None
            reference_artifact_store = durable_artifact_store
            traces_dir = session.traces_dir
            scope = "experiment"
        executor = GraphActionExecutor(
            concept_store=concept_store,
            memory_store=memory_store,
            artifact_store=artifact_store,
            workspace_store=workspace_store,
            state_store=state_store,
            reference_concept_store=reference_concept_store,
            reference_memory_store=reference_memory_store,
            reference_artifact_store=reference_artifact_store,
        )
        chat_service = ChatService(
            model=cfg.model,
            openai_api_key=cfg.openai_api_key,
            concept_store=concept_store,
            reference_concept_store=reference_concept_store,
            memory_store=memory_store,
            memory_trace_store=memory_trace_store,
            artifact_store=artifact_store,
            workspace_store=workspace_store,
            reference_memory_store=reference_memory_store,
            reference_memory_trace_store=reference_memory_trace_store,
            reference_artifact_store=reference_artifact_store,
            vault_store=vault_store,
            search_service=search_service,
            vetting_service=vetting_service,
            meta_service=meta_service,
            executor=executor,
            traces_dir=traces_dir,
        )
        scenario_lab_service = ScenarioLabService(
            model=cfg.model,
            openai_api_key=cfg.openai_api_key,
            concept_store=concept_store,
            reference_concept_store=reference_concept_store,
            memory_store=memory_store,
            memory_trace_store=memory_trace_store,
            artifact_store=artifact_store,
            workspace_store=workspace_store,
            reference_memory_store=reference_memory_store,
            reference_memory_trace_store=reference_memory_trace_store,
            reference_artifact_store=reference_artifact_store,
            vault_store=vault_store,
            search_service=search_service,
            vetting_service=vetting_service,
            traces_dir=traces_dir,
        )
        return {
            "concept_store": concept_store,
            "memory_store": memory_store,
            "memory_trace_store": memory_trace_store,
            "artifact_store": artifact_store,
            "workspace_store": workspace_store,
            "state_store": state_store,
            "executor": executor,
            "chat_service": chat_service,
            "scenario_lab_service": scenario_lab_service,
            "scope": scope,
        }

    def _saved_note_cards(session: ExperimentSession | None) -> list[dict[str, Any]]:
        if session is None:
            return [
                *[_serialize_saved_note_card(memory, scope="durable") for memory in durable_memory_store.list_memories()],
                *[_serialize_saved_note_card(artifact, scope="durable") for artifact in durable_artifact_store.list_artifacts()],
            ]
        experiment_notes = [
            *[_serialize_saved_note_card(memory, scope="experiment") for memory in MemoryStore(session.memories_dir).list_memories()],
            *[_serialize_saved_note_card(artifact, scope="experiment") for artifact in ArtifactStore(session.artifacts_dir).list_artifacts()],
        ]
        durable_notes = [
            *[_serialize_saved_note_card(memory, scope="durable") for memory in durable_memory_store.list_memories()],
            *[_serialize_saved_note_card(artifact, scope="durable") for artifact in durable_artifact_store.list_artifacts()],
        ]
        return experiment_notes + durable_notes

    def _concept_records(session: ExperimentSession | None) -> list[Any]:
        if session is None:
            return durable_concept_store.list_concepts()
        return ConceptStore(session.concepts_dir).list_concepts() + durable_concept_store.list_concepts()

    def _saved_note_records(session: ExperimentSession | None) -> list[Any]:
        if session is None:
            return durable_memory_store.list_memories() + durable_artifact_store.list_artifacts()
        return (
            MemoryStore(session.memories_dir).list_memories()
            + ArtifactStore(session.artifacts_dir).list_artifacts()
            + durable_memory_store.list_memories()
            + durable_artifact_store.list_artifacts()
        )

    def _selected_record_summary(session: ExperimentSession | None, runtime: dict[str, Any], record_id: str | None) -> dict[str, Any] | None:
        if not record_id:
            return None
        stores = [
            (runtime["concept_store"], runtime["scope"]),
            (runtime["memory_store"], runtime["scope"]),
            (runtime["artifact_store"], runtime["scope"]),
            (durable_concept_store if session is not None else None, "durable"),
            (durable_memory_store if session is not None else None, "durable"),
            (durable_artifact_store if session is not None else None, "durable"),
        ]
        for store, scope in stores:
            if store is None:
                continue
            try:
                record = store.get(record_id)
                scenario_metadata = _saved_record_scenario_metadata(record)
                scenario_payload = _scenario_payload(scenario_metadata)
                payload = {
                    "id": record.id,
                    "title": record.title,
                    "card": record.card,
                    "type": record.type,
                    "source": record.source,
                    "scope": scope,
                    "body_excerpt": record.body[:1200],
                    "comes_from": list(record.comes_from),
                    "is_scenario_comparison": (
                        scenario_payload["scenario_kind"] == "comparison"
                        or _is_scenario_comparison_record(record)
                    ),
                }
                payload.update(scenario_payload)
                return payload
            except FileNotFoundError:
                continue
        try:
            note = vault_store.get(record_id)
            return {
                "id": note.id,
                "title": note.title,
                "card": note.card,
                "type": note.type,
                "scenario_kind": None,
                "scenario": None,
                "source": "vault_note",
                "body_excerpt": note.body[:1200],
                "path": note.relative_path,
                "is_scenario_comparison": False,
            }
        except FileNotFoundError:
            return None

    def _chat_turn_response(
        *,
        message: str,
        history: list[dict[str, str]],
        workspace_id: str | None,
        workspace_scope: str,
        workspace_content: str | None,
        whiteboard_mode: str,
        selected_record_id: str | None,
        memory_intent: str,
        pending_workspace_update: dict[str, Any] | None,
        navigation: NavigationDecision | None = None,
        force_pending_workspace_update: bool = False,
    ) -> dict[str, Any]:
        session = experiment_manager.get_active_session()
        runtime = _runtime(session)
        resolved_workspace_id = workspace_id or runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
        normalized_workspace_scope = _normalized_workspace_scope(
            workspace_scope,
            workspace_content=workspace_content,
            user_message=message,
        )
        try:
            workspace = runtime["workspace_store"].load(resolved_workspace_id)
        except FileNotFoundError:
            if normalized_workspace_scope == "excluded":
                workspace = _workspace_from_unsaved_buffer(runtime["workspace_store"], resolved_workspace_id, "")
            elif workspace_content is None:
                raise
            else:
                workspace = _workspace_from_unsaved_buffer(runtime["workspace_store"], resolved_workspace_id, workspace_content)
        transient_workspace = normalized_workspace_scope != "excluded" and workspace_content is not None
        if normalized_workspace_scope == "excluded":
            workspace = _workspace_without_context(workspace)
        elif workspace_content is not None:
            workspace = _workspace_from_buffer(workspace, workspace_content)
        resolved_selected_record_id = selected_record_id
        selected_record = _selected_record_summary(session, runtime, resolved_selected_record_id)
        normalized_pending_workspace_update = _normalized_pending_workspace_update(pending_workspace_update)
        if (
            not force_pending_workspace_update
            and not _should_carry_pending_workspace_update(message, normalized_pending_workspace_update)
        ):
            normalized_pending_workspace_update = None
        if navigation is None:
            navigation = navigator_service.route_turn(
                user_message=message,
                history=history,
                workspace=workspace,
                requested_whiteboard_mode=whiteboard_mode,
                selected_record_id=resolved_selected_record_id,
                selected_record=selected_record,
                pending_workspace_update=normalized_pending_workspace_update,
            )
        resolved_whiteboard_mode = _resolved_whiteboard_mode(
            whiteboard_mode,
            navigation,
            user_message=message,
            workspace=workspace,
        )
        if _should_enter_scenario_lab(navigation):
            try:
                turn = runtime["scenario_lab_service"].run(
                    message=message,
                    workspace=workspace,
                    history=history,
                    navigation=navigation,
                    selected_record_id=resolved_selected_record_id,
                    pending_workspace_update=normalized_pending_workspace_update,
                )
            except Exception as exc:
                scenario_lab_error = {
                    "status": "failed",
                    "navigation": navigation.to_dict(),
                    "selected_record_id": resolved_selected_record_id,
                    "selected_record": selected_record,
                    "comparison_question": navigation.comparison_question,
                    "reason": navigation.reason,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                    "fallback_mode": "chat",
                }
                logger.exception("Scenario Lab request failed unexpectedly. Falling back to normal chat.")
                turn = runtime["chat_service"].reply(
                    message=message,
                    workspace=workspace,
                    history=history,
                    memory_intent=memory_intent,
                    selected_record_id=resolved_selected_record_id,
                    whiteboard_mode=resolved_whiteboard_mode,
                    preserve_selected_record=navigation.preserve_selected_record,
                    selected_record_reason=navigation.selected_record_reason,
                    pending_workspace_update=normalized_pending_workspace_update,
                    workspace_is_transient=transient_workspace,
                    workspace_scope=normalized_workspace_scope,
                )
                payload = _finalize_turn_payload(
                    turn.to_dict(),
                    selected_record_id=resolved_selected_record_id,
                    selected_record=selected_record,
                )
                scenario_lab_error["chat_turn_mode"] = payload.get("mode")
                payload["scenario_lab"] = scenario_lab_error
                payload["scenario_lab_error"] = scenario_lab_error["error"]
                payload["scenario_lab"]["navigation"] = navigation.to_dict()
                payload["scenario_lab"]["selected_record"] = selected_record
                payload["scenario_lab"]["selected_record_id"] = resolved_selected_record_id
                payload["scenario_lab"]["comparison_question"] = navigation.comparison_question
                payload["scenario_lab"]["reason"] = navigation.reason
                payload["scenario_lab"]["error"] = scenario_lab_error["error"]
                payload["scenario_lab"]["status"] = "failed"
                payload["turn_interpretation"] = _turn_interpretation_payload(
                    navigation,
                    requested_whiteboard_mode=whiteboard_mode,
                    resolved_whiteboard_mode=resolved_whiteboard_mode,
                    user_message=message,
                )
                payload["workspace"] = _workspace_payload_for_turn(
                    payload.get("workspace"),
                    workspace=workspace,
                    scope=runtime["scope"],
                    context_scope=normalized_workspace_scope,
                    transient_workspace=transient_workspace,
                )
                payload["experiment"] = _session_info(session)
                return payload
        else:
            turn = runtime["chat_service"].reply(
                message=message,
                workspace=workspace,
                history=history,
                memory_intent=memory_intent,
                selected_record_id=resolved_selected_record_id,
                whiteboard_mode=resolved_whiteboard_mode,
                preserve_selected_record=navigation.preserve_selected_record,
                selected_record_reason=navigation.selected_record_reason,
                pending_workspace_update=normalized_pending_workspace_update,
                workspace_is_transient=transient_workspace,
                workspace_scope=normalized_workspace_scope,
            )
        payload = _finalize_turn_payload(
            turn.to_dict(),
            selected_record_id=resolved_selected_record_id,
            selected_record=selected_record,
        )
        payload["turn_interpretation"] = _turn_interpretation_payload(
            navigation,
            requested_whiteboard_mode=whiteboard_mode,
            resolved_whiteboard_mode=resolved_whiteboard_mode,
            user_message=message,
        )
        payload["workspace"] = _workspace_payload_for_turn(
            payload.get("workspace"),
            workspace=workspace,
            scope=runtime["scope"],
            context_scope=normalized_workspace_scope,
            transient_workspace=transient_workspace,
        )
        payload["experiment"] = _session_info(session)
        return payload

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        session = experiment_manager.get_active_session()
        runtime = _runtime(session)
        state_store = runtime["state_store"]
        return {
            "status": "ok",
            "mode": "openai" if cfg.openai_api_key else "fallback",
            "workspace_id": state_store.get_active_workspace_id(default_workspace_id=cfg.active_workspace),
            "nexus_enabled": vault_store.is_enabled(),
            "experiment": _session_info(session),
        }

    @app.post("/api/experiment/start")
    def start_experiment(request: ExperimentStartRequest) -> dict[str, Any]:
        existing = experiment_manager.get_active_session()
        if existing is not None:
            runtime = _runtime(existing)
            workspace = runtime["workspace_store"].load(
                runtime["state_store"].get_active_workspace_id(default_workspace_id="experiment-workspace")
            )
            return {
                "experiment": _session_info(existing),
                "workspace": _workspace_payload(workspace, scope="experiment"),
            }
        seed_workspace = None
        if request.seed_from_workspace:
            workspace_id = durable_state_store.get_active_workspace_id(default_workspace_id=cfg.active_workspace)
            seed_workspace = durable_workspace_store.load(workspace_id)
        session = experiment_manager.start(seed_workspace=seed_workspace)
        workspace = WorkspaceStore(session.workspaces_dir).load("experiment-workspace")
        return {
            "experiment": _session_info(session),
            "workspace": _workspace_payload(workspace, scope="experiment"),
        }

    @app.post("/api/experiment/end")
    def end_experiment() -> dict[str, Any]:
        ended = experiment_manager.end()
        return {
            "ended": bool(ended),
            "experiment": _session_info(None),
        }

    @app.get("/api/workspace")
    def get_workspace() -> dict[str, Any]:
        session = experiment_manager.get_active_session()
        runtime = _runtime(session)
        workspace_id = runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
        document = runtime["workspace_store"].load(workspace_id)
        return _workspace_payload(document, scope=runtime["scope"])

    @app.post("/api/workspace")
    def update_workspace(request: WorkspaceUpdateRequest) -> dict[str, Any]:
        session = experiment_manager.get_active_session()
        runtime = _runtime(session)
        workspace_id = request.workspace_id or runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
        document = runtime["workspace_store"].save(workspace_id, request.content)
        runtime["state_store"].set_active_workspace_id(document.workspace_id)
        action = runtime["executor"].save_workspace_iteration_artifact(workspace=document)
        artifact = runtime["artifact_store"].get(action.record_id) if action.record_id else None
        return {
            **_workspace_payload(document, scope=runtime["scope"]),
            "graph_action": action.to_dict(),
            "artifact_snapshot": _serialize_saved_note_card(artifact, scope=runtime["scope"]) if artifact else None,
        }

    @app.post("/api/workspace/open")
    def open_workspace(request: WorkspaceOpenRequest) -> dict[str, Any]:
        session = experiment_manager.get_active_session()
        runtime = _runtime(session)
        try:
            document = runtime["workspace_store"].load(request.workspace_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        runtime["state_store"].set_active_workspace_id(document.workspace_id)
        return _workspace_payload(document, scope=runtime["scope"])

    @app.get("/api/concepts")
    def get_concepts() -> dict[str, Any]:
        return {
            "concepts": [
                _serialize_concept_card(concept, scope="experiment" if experiment_manager.get_active_session() and "experiments" in concept.path.parts else "durable")
                for concept in _concept_records(experiment_manager.get_active_session())
            ]
        }

    @app.get("/api/vault-notes")
    def get_vault_notes() -> dict[str, Any]:
        return {"vault_notes": [_serialize_vault_note_card(note) for note in vault_store.list_notes()]}

    @app.get("/api/memory")
    def get_memory() -> dict[str, Any]:
        return _memory_payload(
            _saved_note_cards(experiment_manager.get_active_session()),
            [_serialize_vault_note_card(note) for note in vault_store.list_notes()],
        )

    @app.get("/api/concepts/search")
    def search_concepts(query: str) -> dict[str, Any]:
        candidates = search_service.search(
            query=query,
            concepts=_concept_records(experiment_manager.get_active_session()),
            limit=10,
        )
        return {"concepts": [candidate.to_dict() for candidate in candidates]}

    @app.get("/api/vault-notes/search")
    def search_vault_notes(query: str) -> dict[str, Any]:
        candidates = search_service.search(
            query=query,
            records=vault_store.list_notes(),
            limit=10,
        )
        return {"vault_notes": [candidate.to_dict() for candidate in candidates]}

    @app.get("/api/memory/search")
    def search_memory(query: str) -> dict[str, Any]:
        candidates = search_service.search_memory(
            query=query,
            saved_note_records=_saved_note_records(experiment_manager.get_active_session()),
            vault_records=vault_store.list_notes(),
            limit=12,
        )
        saved_notes = [candidate.to_dict() for candidate in candidates if candidate.source in {"memory", "artifact"}]
        reference_notes = [candidate.to_dict() for candidate in candidates if candidate.source == "vault_note"]
        return {
            **_memory_payload(saved_notes, reference_notes),
            "results": [candidate.to_dict() for candidate in candidates],
            "memory": [candidate.to_dict() for candidate in candidates],
            "saved_notes_results": saved_notes,
            "vault_notes": reference_notes,
        }

    @app.get("/api/memory/{memory_id}")
    def get_memory_item(memory_id: str) -> dict[str, Any]:
        session = experiment_manager.get_active_session()
        runtime = _runtime(session)
        for store, scope in [
            (runtime["memory_store"], runtime["scope"]),
            (runtime["artifact_store"], runtime["scope"]),
            (durable_memory_store if session is not None else None, "durable"),
            (durable_artifact_store if session is not None else None, "durable"),
        ]:
            if store is None:
                continue
            try:
                note = store.get(memory_id)
                item = _serialize_saved_note_card(note, scope=scope)
                item["kind"] = "saved_note"
                return {"item": item, "kind": "saved_note"}
            except FileNotFoundError:
                continue
        try:
            note = vault_store.get(memory_id)
            item = _serialize_vault_note_card(note)
            item["kind"] = "reference_note"
            return {"item": item, "kind": "reference_note"}
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/concepts/{concept_id}")
    def get_concept(concept_id: str) -> dict[str, Any]:
        session = experiment_manager.get_active_session()
        runtime = _runtime(session)
        try:
            concept = runtime["concept_store"].get(concept_id)
            return _serialize_concept_card(concept, scope=runtime["scope"])
        except FileNotFoundError:
            concept = durable_concept_store.get(concept_id)
            return _serialize_concept_card(concept, scope="durable")

    @app.get("/api/vault-notes/{note_id}")
    def get_vault_note(note_id: str) -> dict[str, Any]:
        note = vault_store.get(note_id)
        return _serialize_vault_note_card(note)

    @app.post("/api/concepts/promote")
    def promote_workspace(request: ConceptPromotionRequest) -> dict[str, Any]:
        session = experiment_manager.get_active_session()
        runtime = _runtime(session)
        workspace_id = request.workspace_id or runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
        workspace = runtime["workspace_store"].load(workspace_id)
        if request.content is not None:
            workspace = runtime["workspace_store"].save(workspace_id, request.content)
        action = runtime["executor"].promote_workspace(
            workspace=workspace,
            title=request.title,
            card=request.card,
        )
        artifact = runtime["artifact_store"].get(action.record_id) if action.record_id else None
        return {
            "graph_action": action.to_dict(),
            "promoted_record": _serialize_saved_note_card(artifact, scope=runtime["scope"]) if artifact else None,
            "promoted_concept": None,
        }

    @app.post("/api/concepts/open")
    def open_concept(request: ConceptOpenRequest) -> dict[str, Any]:
        session = experiment_manager.get_active_session()
        runtime = _runtime(session)
        record_id = request.record_id or request.concept_id
        if not record_id:
            raise HTTPException(status_code=400, detail="record_id or concept_id is required.")
        action = runtime["executor"].open_saved_item_into_workspace(record_id)
        workspace = runtime["workspace_store"].load(action.workspace_id or record_id)
        payload = _workspace_payload(workspace, scope=runtime["scope"])
        payload["graph_action"] = action.to_dict()
        return payload

    @app.post("/api/chat")
    def chat(request: ChatRequest) -> dict[str, Any]:
        try:
            return _chat_turn_response(
                message=request.message,
                history=request.history,
                workspace_id=request.workspace_id,
                workspace_scope=request.workspace_scope,
                workspace_content=request.workspace_content,
                whiteboard_mode=request.whiteboard_mode,
                selected_record_id=request.selected_record_id,
                memory_intent=request.memory_intent,
                pending_workspace_update=request.pending_workspace_update,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Chat request failed unexpectedly.")
            raise HTTPException(status_code=500, detail="Chat request failed unexpectedly.") from exc

    @app.post("/api/chat/whiteboard/accept")
    def accept_whiteboard(request: WhiteboardAcceptRequest) -> dict[str, Any]:
        normalized_pending_workspace_update = _normalized_pending_workspace_update(request.pending_workspace_update)
        if not normalized_pending_workspace_update:
            raise HTTPException(status_code=400, detail="pending_workspace_update is required.")
        origin_user_message = normalized_pending_workspace_update.get("origin_user_message")
        if not origin_user_message:
            raise HTTPException(status_code=400, detail="pending_workspace_update.origin_user_message is required.")
        try:
            return _chat_turn_response(
                message=origin_user_message,
                history=request.history,
                workspace_id=request.workspace_id,
                workspace_scope=request.workspace_scope,
                workspace_content=request.workspace_content,
                whiteboard_mode="draft",
                selected_record_id=request.selected_record_id,
                memory_intent=request.memory_intent,
                pending_workspace_update=normalized_pending_workspace_update,
                navigation=NavigationDecision(
                    mode="chat",
                    confidence=1.0,
                    reason="Pending whiteboard offer accepted through the dedicated acceptance route.",
                    whiteboard_mode="draft",
                ),
                force_pending_workspace_update=True,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Whiteboard acceptance request failed unexpectedly.")
            raise HTTPException(status_code=500, detail="Whiteboard acceptance request failed unexpectedly.") from exc

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    return app


def main() -> None:
    config = AppConfig.from_env()
    uvicorn.run(
        create_app(config),
        host="127.0.0.1",
        port=config.port,
    )


def _should_enter_scenario_lab(decision: NavigationDecision) -> bool:
    return decision.mode == "scenario_lab" and decision.confidence >= SCENARIO_LAB_MIN_CONFIDENCE


def _scenario_kind_for_record_type(record_type: str) -> str | None:
    if record_type == "scenario_comparison":
        return "comparison"
    return None


def _resolved_whiteboard_mode(
    requested_whiteboard_mode: str | None,
    decision: NavigationDecision,
    *,
    user_message: str | None,
    workspace: WorkspaceDocument,
) -> str:
    if requested_whiteboard_mode == "chat":
        return requested_whiteboard_mode
    if _is_explicit_whiteboard_draft_request(user_message) and decision.mode == "chat":
        return "draft"
    if (
        decision.mode == "chat"
        and requested_whiteboard_mode != "chat"
        and _should_continue_current_whiteboard_draft(user_message, workspace)
    ):
        return "draft"
    if requested_whiteboard_mode in {"offer", "draft"}:
        return requested_whiteboard_mode
    if decision.whiteboard_mode in {"chat", "offer", "draft", "auto"}:
        return decision.whiteboard_mode
    return "auto"


def _turn_interpretation_payload(
    decision: NavigationDecision,
    *,
    requested_whiteboard_mode: str | None,
    resolved_whiteboard_mode: str,
    user_message: str | None,
) -> dict[str, Any]:
    requested_mode = _normalized_requested_whiteboard_mode(requested_whiteboard_mode)
    return {
        "mode": decision.mode,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "requested_whiteboard_mode": requested_mode,
        "resolved_whiteboard_mode": resolved_whiteboard_mode if decision.mode == "chat" else None,
        "whiteboard_mode_source": _whiteboard_mode_source(
            requested_mode,
            decision,
            resolved_whiteboard_mode,
            user_message=user_message,
        ),
        "preserve_selected_record": decision.preserve_selected_record,
        "selected_record_reason": decision.selected_record_reason,
    }


def _normalized_requested_whiteboard_mode(value: str | None) -> str:
    if value in {"chat", "offer", "draft", "auto"}:
        return value
    return "auto"


def _whiteboard_mode_source(
    requested_whiteboard_mode: str,
    decision: NavigationDecision,
    resolved_whiteboard_mode: str,
    *,
    user_message: str | None,
) -> str | None:
    if decision.mode != "chat":
        return None
    if requested_whiteboard_mode == "chat":
        return "composer"
    if _is_explicit_whiteboard_draft_request(user_message) and resolved_whiteboard_mode == "draft":
        return "request"
    if requested_whiteboard_mode in {"offer", "draft"}:
        return "composer"
    if decision.whiteboard_mode in {"chat", "offer", "draft", "auto"}:
        return "interpreter"
    if resolved_whiteboard_mode == "auto":
        return "default"
    return None


def _is_explicit_whiteboard_draft_request(message: str | None) -> bool:
    if not message:
        return False
    return bool(
        EXPLICIT_WHITEBOARD_OPEN_RE.search(message)
        or EXPLICIT_WHITEBOARD_DRAFT_RE.search(message)
    )


def _should_continue_current_whiteboard_draft(
    message: str | None,
    workspace: WorkspaceDocument,
) -> bool:
    if not message or not workspace.content.strip():
        return False
    if not WHITEBOARD_EDIT_VERB_RE.search(message):
        return False
    return bool(WHITEBOARD_EDIT_TARGET_RE.search(message))


def _normalize_message(message: str | None) -> str:
    return str(message or "").strip()


def _is_pending_accept_follow_up(text: str) -> bool:
    if not text:
        return True
    if len(text) > MAX_PENDING_FOLLOW_UP_LENGTH:
        return False
    if PENDING_ACCEPT_RE.search(text):
        return True
    return bool(PENDING_CONTINUE_RE.search(text) and PENDING_REFERENCE_RE.search(text))


def _is_pending_edit_follow_up(text: str) -> bool:
    if not text or len(text) > MAX_PENDING_FOLLOW_UP_LENGTH:
        return False
    return bool(WHITEBOARD_EDIT_VERB_RE.search(text) and PENDING_EDIT_TARGET_RE.search(text))


def _should_carry_pending_workspace_update(
    message: str | None,
    pending_workspace_update: dict[str, Any] | None,
) -> bool:
    if not _is_pending_workspace_update_active(pending_workspace_update):
        return False
    text = _normalize_message(message)
    if _is_explicit_whiteboard_draft_request(text):
        return True
    if _is_pending_accept_follow_up(text):
        return True
    if _is_pending_edit_follow_up(text):
        return True
    return False


def _normalized_workspace_scope(
    value: str | None,
    *,
    workspace_content: str | None,
    user_message: str | None,
) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"excluded", "visible", "pinned", "requested"}:
        return normalized
    if workspace_content is not None:
        return "visible"
    if _is_explicit_whiteboard_draft_request(user_message):
        return "requested"
    return "excluded"


def _normalized_pending_workspace_update(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    workspace_type = str(value.get("type") or "").strip() or None
    workspace_status = str(value.get("status") or "").strip() or None
    if workspace_status is None and workspace_type is not None:
        workspace_status = WHITEBOARD_TYPE_TO_STATUS.get(workspace_type)
    if workspace_type is None and workspace_status is not None:
        workspace_type = WHITEBOARD_STATUS_TO_TYPE.get(workspace_status)
    normalized = {
        "type": workspace_type,
        "status": workspace_status,
        "summary": str(value.get("summary") or "").strip() or None,
        "origin_user_message": str(value.get("origin_user_message") or "").strip() or None,
        "origin_assistant_message": str(value.get("origin_assistant_message") or "").strip() or None,
    }
    if not any(normalized.values()):
        return None
    return normalized


def _is_pending_workspace_update_active(value: dict[str, Any] | None) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        value.get("type") in {"offer_whiteboard", "draft_whiteboard"}
        and value.get("status") in {"offered", "draft_ready"}
        and bool(value.get("origin_user_message"))
    )


def _is_scenario_comparison_record(record: Any) -> bool:
    if getattr(record, "type", None) == "scenario_comparison":
        return True
    body = getattr(record, "body", "")
    return "## Recommendation" in body and "## Branches Compared" in body
