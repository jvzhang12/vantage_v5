from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
import re
import secrets
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from vantage_v5.config import AppConfig
from vantage_v5.services.chat import ChatService
from vantage_v5.services.context_engine import ChatTurnRequestContext
from vantage_v5.services.context_engine import ContextEngine
from vantage_v5.services.context_engine import ContextEngineHooks
from vantage_v5.services.context_sources import ContextSourceResolver
from vantage_v5.services.context_support import ContextSupport
from vantage_v5.services.draft_artifact_lifecycle import DraftArtifactLifecycle
from vantage_v5.services.draft_artifact_lifecycle import DraftArtifactRuntime
from vantage_v5.services.executor import GraphActionExecutor
from vantage_v5.services.local_semantic_actions import LocalSemanticActionEngine
from vantage_v5.services.meta import MetaService
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.navigator import NavigatorService
from vantage_v5.services.record_cards import memory_payload as _memory_payload
from vantage_v5.services.record_cards import scenario_payload as _scenario_payload
from vantage_v5.services.record_cards import serialize_built_in_protocol_card as _serialize_built_in_protocol
from vantage_v5.services.record_cards import serialize_concept_card as _serialize_concept_card
from vantage_v5.services.record_cards import serialize_saved_note_card as _serialize_saved_note_card
from vantage_v5.services.record_cards import serialize_vault_note_card as _serialize_vault_note_card
from vantage_v5.services.protocol_engine import ProtocolEngine
from vantage_v5.services.scenario_lab import ScenarioLabService
from vantage_v5.services.search import ConceptSearchService
from vantage_v5.services.turn_orchestrator import TurnOrchestrator
from vantage_v5.services.turn_orchestrator import TurnOrchestratorHooks
from vantage_v5.services.vetting import ConceptVettingService
from vantage_v5.services.whiteboard_routing import WhiteboardRoutingEngine
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.experiments import ExperimentSession
from vantage_v5.storage.experiments import ExperimentSessionManager
from vantage_v5.storage.memory_trace import MemoryTraceStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.state import ActiveWorkspaceStateStore
from vantage_v5.storage.vault import VaultNoteStore
from vantage_v5.storage.workspaces import WorkspaceStore


logger = logging.getLogger(__name__)
SCENARIO_LAB_MIN_CONFIDENCE = 0.68
CONTENT_UNSET = object()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)
    workspace_id: str | None = None
    workspace_scope: str = "auto"
    workspace_content: str | None = None
    whiteboard_mode: str = "auto"
    pinned_context_id: str | None = None
    selected_record_id: str | None = None
    memory_intent: str = "auto"
    pending_workspace_update: dict[str, Any] | None = None


class WhiteboardAcceptRequest(BaseModel):
    history: list[dict[str, str]] = Field(default_factory=list)
    workspace_id: str | None = None
    workspace_scope: str = "auto"
    workspace_content: str | None = None
    pinned_context_id: str | None = None
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


class ProtocolUpdateRequest(BaseModel):
    title: str | None = None
    card: str | None = None
    body: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    applies_to: list[str] | None = None


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


def _resolve_pinned_context_id(
    *,
    pinned_context_id: str | None,
    selected_record_id: str | None,
) -> str | None:
    return pinned_context_id or selected_record_id


def create_app(config: AppConfig | None = None) -> FastAPI:
    cfg = config or AppConfig.from_env()
    repo_root = cfg.repo_root
    multi_user_enabled = bool(cfg.auth_users)
    durable_scope_cache: dict[str, dict[str, Any]] = {}
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
    protocol_engine = ProtocolEngine(
        model=cfg.model,
        openai_api_key=cfg.openai_api_key,
    )
    draft_artifact_lifecycle = DraftArtifactLifecycle()
    local_semantic_actions = LocalSemanticActionEngine(
        draft_artifact_lifecycle=draft_artifact_lifecycle,
    )
    whiteboard_routing = WhiteboardRoutingEngine()
    context_support = ContextSupport(
        whiteboard_routing=whiteboard_routing,
    )
    context_sources = ContextSourceResolver(vault_store=vault_store)

    app = FastAPI(title="Vantage V5", version="0.1.0")
    web_dir = Path(__file__).resolve().parent / "webapp"
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.middleware("http")
    async def _basic_auth_middleware(request: Request, call_next):
        request.state.user_id = None
        auth_enabled = bool(cfg.auth_password or cfg.auth_users)
        if not auth_enabled:
            if not multi_user_enabled:
                request.state.user_id = cfg.auth_username
            return await call_next(request)
        authorized_user = _basic_auth_authorized_user(
            request.headers.get("authorization"),
            username=cfg.auth_username,
            password=cfg.auth_password,
            users=cfg.auth_users,
        )
        if request.url.path == "/api/health":
            request.state.user_id = authorized_user
            return await call_next(request)
        if authorized_user:
            request.state.user_id = authorized_user
            return await call_next(request)
        return Response(
            "Authentication required.",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Vantage"'},
        )

    def _scope_key_for_request(request: Request | None) -> str:
        if not multi_user_enabled:
            return "__single_user__"
        user_id = str(getattr(getattr(request, "state", None), "user_id", "") or "").strip()
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return _safe_user_storage_id(user_id)

    def _user_root_for_key(scope_key: str) -> Path:
        if scope_key == "__single_user__":
            return repo_root
        return repo_root / "users" / scope_key

    def _ensure_storage_root(root: Path) -> None:
        for folder in ["concepts", "memories", "memory_trace", "artifacts", "workspaces", "state", "traces"]:
            (root / folder).mkdir(parents=True, exist_ok=True)
        workspace_path = root / "workspaces" / f"{cfg.active_workspace}.md"
        if not workspace_path.exists():
            workspace_path.write_text(
                "# Working Draft\n\n"
                "This is your private Vantage draft. Ask naturally, then save or publish useful work when it is ready.\n",
                encoding="utf-8",
            )
        state_path = root / "state" / "active_workspace.json"
        if not state_path.exists():
            state_path.write_text(
                json.dumps(
                    {
                        "active_workspace_id": cfg.active_workspace,
                        "active_workspace_path": f"workspaces/{cfg.active_workspace}.md",
                        "status": "active",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    def _durable_scope(request: Request | None = None) -> dict[str, Any]:
        scope_key = _scope_key_for_request(request)
        cached = durable_scope_cache.get(scope_key)
        if cached is not None:
            return cached
        root = _user_root_for_key(scope_key)
        if multi_user_enabled:
            _ensure_storage_root(root)
        scope = {
            "user_id": None if scope_key == "__single_user__" else scope_key,
            "root": root,
            "concept_store": ConceptStore(root / "concepts"),
            "memory_store": MemoryStore(root / "memories"),
            "memory_trace_store": MemoryTraceStore(root / "memory_trace"),
            "artifact_store": ArtifactStore(root / "artifacts"),
            "workspace_store": WorkspaceStore(root / "workspaces"),
            "state_store": ActiveWorkspaceStateStore(root / "state" / "active_workspace.json"),
            "experiment_manager": ExperimentSessionManager(root / "state"),
            "traces_dir": root / "traces",
        }
        durable_scope_cache[scope_key] = scope
        return scope

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

    def _runtime(durable_scope: dict[str, Any], session: ExperimentSession | None) -> dict[str, Any]:
        if session is None:
            concept_store = durable_scope["concept_store"]
            memory_store = durable_scope["memory_store"]
            memory_trace_store = durable_scope["memory_trace_store"]
            artifact_store = durable_scope["artifact_store"]
            workspace_store = durable_scope["workspace_store"]
            state_store = durable_scope["state_store"]
            reference_concept_store = None
            reference_memory_store = None
            reference_memory_trace_store = None
            reference_artifact_store = None
            traces_dir = durable_scope["traces_dir"]
            scope = "durable"
        else:
            concept_store = ConceptStore(session.concepts_dir)
            memory_store = MemoryStore(session.memories_dir)
            memory_trace_store = MemoryTraceStore(session.memory_trace_dir)
            artifact_store = ArtifactStore(session.artifacts_dir)
            workspace_store = WorkspaceStore(session.workspaces_dir)
            state_store = ActiveWorkspaceStateStore(session.state_path)
            reference_concept_store = durable_scope["concept_store"]
            reference_memory_store = durable_scope["memory_store"]
            reference_memory_trace_store = None
            reference_artifact_store = durable_scope["artifact_store"]
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
            protocol_engine=protocol_engine,
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
            protocol_engine=protocol_engine,
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

    def _saved_note_cards(durable_scope: dict[str, Any], session: ExperimentSession | None) -> list[dict[str, Any]]:
        if session is None:
            return [
                *[_serialize_saved_note_card(memory, scope="durable") for memory in durable_scope["memory_store"].list_memories()],
                *[_serialize_saved_note_card(artifact, scope="durable") for artifact in durable_scope["artifact_store"].list_artifacts()],
            ]
        experiment_notes = [
            *[_serialize_saved_note_card(memory, scope="experiment") for memory in MemoryStore(session.memories_dir).list_memories()],
            *[_serialize_saved_note_card(artifact, scope="experiment") for artifact in ArtifactStore(session.artifacts_dir).list_artifacts()],
        ]
        durable_notes = [
            *[_serialize_saved_note_card(memory, scope="durable") for memory in durable_scope["memory_store"].list_memories()],
            *[_serialize_saved_note_card(artifact, scope="durable") for artifact in durable_scope["artifact_store"].list_artifacts()],
        ]
        return experiment_notes + durable_notes

    def _concept_records(durable_scope: dict[str, Any], session: ExperimentSession | None) -> list[Any]:
        if session is None:
            return durable_scope["concept_store"].list_concepts()
        return ConceptStore(session.concepts_dir).list_concepts() + durable_scope["concept_store"].list_concepts()

    def _record_scope(record: Any, session: ExperimentSession | None) -> str:
        return "experiment" if session and "experiments" in record.path.parts else "durable"

    def _serialize_protocol_catalog_entry(entry: Any, session: ExperimentSession | None) -> dict[str, Any]:
        if entry.record is not None:
            return _serialize_concept_card(entry.record, scope=_record_scope(entry.record, session))
        if entry.built_in_kind is None:
            raise HTTPException(status_code=500, detail="Protocol catalog entry is incomplete.")
        return _serialize_built_in_protocol(entry.built_in_kind)

    def _saved_note_records(durable_scope: dict[str, Any], session: ExperimentSession | None) -> list[Any]:
        if session is None:
            return durable_scope["memory_store"].list_memories() + durable_scope["artifact_store"].list_artifacts()
        return (
            MemoryStore(session.memories_dir).list_memories()
            + ArtifactStore(session.artifacts_dir).list_artifacts()
            + durable_scope["memory_store"].list_memories()
            + durable_scope["artifact_store"].list_artifacts()
        )

    context_engine = ContextEngine(
        default_workspace_id=cfg.active_workspace,
        context_support=context_support,
        hooks=ContextEngineHooks(
            runtime_for=_runtime,
            pinned_context_summary=context_sources.pinned_context_summary,
            whiteboard_source_summary=context_sources.whiteboard_source_summary,
            navigator_continuity_context=context_sources.navigator_continuity_context,
        ),
    )
    turn_orchestrator = TurnOrchestrator(
        navigator_service=navigator_service,
        context_engine=context_engine,
        protocol_engine=protocol_engine,
        local_semantic_actions=local_semantic_actions,
        whiteboard_routing=whiteboard_routing,
        hooks=TurnOrchestratorHooks(
            should_enter_scenario_lab=_should_enter_scenario_lab,
        ),
    )

    def _chat_turn_response(
        *,
        durable_scope: dict[str, Any],
        message: str,
        history: list[dict[str, str]],
        workspace_id: str | None,
        workspace_scope: str,
        workspace_content: str | None,
        whiteboard_mode: str,
        pinned_context_id: str | None,
        memory_intent: str,
        pending_workspace_update: dict[str, Any] | None,
        navigation: NavigationDecision | None = None,
        force_pending_workspace_update: bool = False,
    ) -> dict[str, Any]:
        return turn_orchestrator.run(
            ChatTurnRequestContext(
                durable_scope=durable_scope,
                message=message,
                history=history,
                workspace_id=workspace_id,
                workspace_scope=workspace_scope,
                workspace_content=workspace_content,
                whiteboard_mode=whiteboard_mode,
                pinned_context_id=pinned_context_id,
                memory_intent=memory_intent,
                pending_workspace_update=pending_workspace_update,
                navigation=navigation,
                force_pending_workspace_update=force_pending_workspace_update,
            )
        )

    @app.get("/api/health")
    def health(request: Request) -> dict[str, Any]:
        user_id = str(getattr(request.state, "user_id", "") or "")
        if multi_user_enabled:
            workspace_id = None
            experiment = {"active": False, "session_id": None, "saved_note_count": 0}
            if user_id:
                durable_scope = _durable_scope(request)
                session = durable_scope["experiment_manager"].get_active_session()
                runtime = _runtime(durable_scope, session)
                workspace_id = runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
                experiment = _session_info(session)
        else:
            durable_scope = _durable_scope()
            session = durable_scope["experiment_manager"].get_active_session()
            runtime = _runtime(durable_scope, session)
            workspace_id = runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
            experiment = _session_info(session)
        return {
            "status": "ok",
            "mode": "openai" if cfg.openai_api_key else "fallback",
            "workspace_id": workspace_id,
            "nexus_enabled": vault_store.is_enabled(),
            "experiment": experiment,
            "multi_user": multi_user_enabled,
            "user": {"id": user_id} if user_id else None,
        }

    @app.post("/api/experiment/start")
    def start_experiment(request: ExperimentStartRequest, http_request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        experiment_manager = durable_scope["experiment_manager"]
        existing = experiment_manager.get_active_session()
        if existing is not None:
            runtime = _runtime(durable_scope, existing)
            workspace = runtime["workspace_store"].load(
                runtime["state_store"].get_active_workspace_id(default_workspace_id="experiment-workspace")
            )
            return {
                "experiment": _session_info(existing),
                "workspace": _workspace_payload(workspace, scope="experiment"),
            }
        seed_workspace = None
        if request.seed_from_workspace:
            workspace_id = durable_scope["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
            seed_workspace = durable_scope["workspace_store"].load(workspace_id)
        session = experiment_manager.start(seed_workspace=seed_workspace)
        workspace = WorkspaceStore(session.workspaces_dir).load("experiment-workspace")
        return {
            "experiment": _session_info(session),
            "workspace": _workspace_payload(workspace, scope="experiment"),
        }

    @app.post("/api/experiment/end")
    def end_experiment(http_request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        ended = durable_scope["experiment_manager"].end()
        return {
            "ended": bool(ended),
            "experiment": _session_info(None),
        }

    @app.get("/api/workspace")
    def get_workspace(request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        workspace_id = runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
        document = runtime["workspace_store"].load(workspace_id)
        return _workspace_payload(document, scope=runtime["scope"])

    @app.post("/api/workspace")
    def update_workspace(request: WorkspaceUpdateRequest, http_request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        workspace_id = request.workspace_id or runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
        result = draft_artifact_lifecycle.save_workspace_update(
            runtime=DraftArtifactRuntime.from_mapping(runtime),
            workspace_id=workspace_id,
            content=request.content,
        )
        return {
            **_workspace_payload(result.workspace, scope=result.scope),
            "graph_action": result.graph_action,
            "artifact_snapshot": _serialize_saved_note_card(result.artifact, scope=result.scope) if result.artifact else None,
        }

    @app.post("/api/workspace/open")
    def open_workspace(request: WorkspaceOpenRequest, http_request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        try:
            document = runtime["workspace_store"].load(request.workspace_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        runtime["state_store"].set_active_workspace_id(document.workspace_id)
        return _workspace_payload(document, scope=runtime["scope"])

    @app.get("/api/concepts")
    def get_concepts(request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        return {
            "concepts": [
                _serialize_concept_card(concept, scope=_record_scope(concept, session))
                for concept in _concept_records(durable_scope, session)
            ]
        }

    @app.get("/api/protocols")
    def get_protocols(request: Request, include_builtins: bool = False) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        catalog = protocol_engine.list_catalog(
            concept_records=_concept_records(durable_scope, session),
            include_builtins=include_builtins,
        )
        return {
            "protocols": [
                _serialize_protocol_catalog_entry(entry, session)
                for entry in catalog.entries
            ]
        }

    @app.get("/api/protocols/{protocol_kind_or_id}")
    def get_protocol(protocol_kind_or_id: str, request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        entry = protocol_engine.lookup_catalog_entry(
            concept_records=_concept_records(durable_scope, session),
            protocol_kind_or_id=protocol_kind_or_id,
        )
        if entry is not None:
            return _serialize_protocol_catalog_entry(entry, session)
        raise HTTPException(status_code=404, detail=f"Protocol '{protocol_kind_or_id}' was not found.")

    @app.put("/api/protocols/{protocol_kind}")
    def put_protocol(protocol_kind: str, request: ProtocolUpdateRequest, http_request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        try:
            protocol = protocol_engine.update_from_api(
                protocol_kind=protocol_kind,
                concept_records=_concept_records(durable_scope, session),
                concept_store=runtime["concept_store"],
                title=request.title,
                card=request.card,
                body=request.body,
                variables=request.variables,
                applies_to=request.applies_to,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_concept_card(protocol, scope=runtime["scope"])

    @app.get("/api/vault-notes")
    def get_vault_notes() -> dict[str, Any]:
        return {"vault_notes": [_serialize_vault_note_card(note) for note in vault_store.list_notes()]}

    @app.get("/api/memory")
    def get_memory(request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        return _memory_payload(
            _saved_note_cards(durable_scope, session),
            [_serialize_vault_note_card(note) for note in vault_store.list_notes()],
        )

    @app.get("/api/concepts/search")
    def search_concepts(query: str, request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        candidates = search_service.search(
            query=query,
            concepts=_concept_records(durable_scope, session),
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
    def search_memory(query: str, request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        candidates = search_service.search_memory(
            query=query,
            saved_note_records=_saved_note_records(durable_scope, session),
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
    def get_memory_item(memory_id: str, request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        for store, scope in [
            (runtime["memory_store"], runtime["scope"]),
            (runtime["artifact_store"], runtime["scope"]),
            (durable_scope["memory_store"] if session is not None else None, "durable"),
            (durable_scope["artifact_store"] if session is not None else None, "durable"),
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
    def get_concept(concept_id: str, request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        try:
            concept = runtime["concept_store"].get(concept_id)
            return _serialize_concept_card(concept, scope=runtime["scope"])
        except FileNotFoundError:
            concept = durable_scope["concept_store"].get(concept_id)
            return _serialize_concept_card(concept, scope="durable")

    @app.get("/api/vault-notes/{note_id}")
    def get_vault_note(note_id: str) -> dict[str, Any]:
        note = vault_store.get(note_id)
        return _serialize_vault_note_card(note)

    @app.post("/api/concepts/promote")
    def promote_workspace(request: ConceptPromotionRequest, http_request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        workspace_id = request.workspace_id or runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
        result = draft_artifact_lifecycle.promote_whiteboard_to_artifact(
            runtime=DraftArtifactRuntime.from_mapping(runtime),
            workspace_id=workspace_id,
            content=request.content,
            title=request.title,
            card=request.card,
        )
        return {
            "graph_action": result.graph_action,
            "promoted_record": _serialize_saved_note_card(result.artifact, scope=result.scope) if result.artifact else None,
            "promoted_concept": None,
        }

    @app.post("/api/concepts/open")
    def open_concept(request: ConceptOpenRequest, http_request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        record_id = (request.record_id or request.concept_id or "").strip()
        if not record_id:
            raise HTTPException(status_code=400, detail="record_id or concept_id is required.")
        try:
            result = draft_artifact_lifecycle.open_saved_item_into_whiteboard(
                runtime=DraftArtifactRuntime.from_mapping(runtime),
                record_id=record_id,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = _workspace_payload(result.workspace, scope=result.scope)
        payload["graph_action"] = result.graph_action
        return payload

    @app.post("/api/chat")
    def chat(request: ChatRequest, http_request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        try:
            return _chat_turn_response(
                durable_scope=durable_scope,
                message=request.message,
                history=request.history,
                workspace_id=request.workspace_id,
                workspace_scope=request.workspace_scope,
                workspace_content=request.workspace_content,
                whiteboard_mode=request.whiteboard_mode,
                pinned_context_id=_resolve_pinned_context_id(
                    pinned_context_id=request.pinned_context_id,
                    selected_record_id=request.selected_record_id,
                ),
                memory_intent=request.memory_intent,
                pending_workspace_update=request.pending_workspace_update,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Chat request failed unexpectedly.")
            raise HTTPException(status_code=500, detail="Chat request failed unexpectedly.") from exc

    @app.post("/api/chat/whiteboard/accept")
    def accept_whiteboard(request: WhiteboardAcceptRequest, http_request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        normalized_pending_workspace_update = context_support.normalize_pending_workspace_update(
            request.pending_workspace_update
        )
        if not normalized_pending_workspace_update:
            raise HTTPException(status_code=400, detail="pending_workspace_update is required.")
        origin_user_message = normalized_pending_workspace_update.get("origin_user_message")
        if not origin_user_message:
            raise HTTPException(status_code=400, detail="pending_workspace_update.origin_user_message is required.")
        try:
            return _chat_turn_response(
                durable_scope=durable_scope,
                message=origin_user_message,
                history=request.history,
                workspace_id=request.workspace_id,
                workspace_scope=request.workspace_scope,
                workspace_content=request.workspace_content,
                whiteboard_mode="draft",
                pinned_context_id=_resolve_pinned_context_id(
                    pinned_context_id=request.pinned_context_id,
                    selected_record_id=request.selected_record_id,
                ),
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
        host=config.host,
        port=config.port,
    )


def _basic_auth_authorized_user(
    authorization: str | None,
    *,
    username: str,
    password: str | None,
    users: dict[str, str] | None = None,
) -> str | None:
    scheme, _, token = str(authorization or "").partition(" ")
    if scheme.lower() != "basic" or not token:
        return None
    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    supplied_username, separator, supplied_password = decoded.partition(":")
    if not separator:
        return None
    for expected_username, expected_password in (users or {}).items():
        if secrets.compare_digest(supplied_username, expected_username) and secrets.compare_digest(
            supplied_password,
            expected_password,
        ):
            return expected_username
    if password and secrets.compare_digest(supplied_username, username) and secrets.compare_digest(
        supplied_password,
        password,
    ):
        return username
    return None


def _safe_user_storage_id(username: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", username.strip().lower()).strip(".-")
    if not normalized:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return normalized[:80]


def _should_enter_scenario_lab(decision: NavigationDecision) -> bool:
    return decision.mode == "scenario_lab" and decision.confidence >= SCENARIO_LAB_MIN_CONFIDENCE
