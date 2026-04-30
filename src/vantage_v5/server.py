from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
from ipaddress import ip_address
import json
import logging
from pathlib import Path
import re
import secrets
from typing import Any
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from vantage_v5.config import AppConfig
from vantage_v5.services.chat import ChatService
from vantage_v5.services.context_engine import ChatTurnRequestContext
from vantage_v5.services.context_engine import ContextEngine
from vantage_v5.services.context_engine import ContextEngineHooks
from vantage_v5.services.context_sources import ContextSourceResolver
from vantage_v5.services.context_support import ContextSupport
from vantage_v5.services.corrections import CorrectionRejected
from vantage_v5.services.corrections import SavedItemCorrectionService
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
from vantage_v5.storage.overlay import ArtifactOverlayStore
from vantage_v5.storage.overlay import ConceptOverlayStore
from vantage_v5.storage.overlay import MemoryOverlayStore
from vantage_v5.storage.overlay import get_overlay_record
from vantage_v5.storage.overlay import overlay_records
from vantage_v5.storage.state import ActiveWorkspaceStateStore
from vantage_v5.storage.vault import VaultNoteStore
from vantage_v5.storage.workspaces import WorkspaceStore


logger = logging.getLogger(__name__)
SCENARIO_LAB_MIN_CONFIDENCE = 0.68
ACCOUNT_PASSWORD_ITERATIONS = 310_000
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


class RecordCorrectionRequest(BaseModel):
    action: str = Field(min_length=1)
    reason: str | None = None
    scope: str = "current"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class CreateAccountRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=4096)


class OpenAIKeyRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=4096)


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
    account_store_path = repo_root / "state" / "accounts.json"
    auth_enabled = bool(cfg.auth_password or cfg.auth_users or account_store_path.exists())
    if _requires_public_auth(cfg.host) and not auth_enabled and not cfg.allow_unsafe_public_no_auth:
        raise RuntimeError(
            "Vantage is configured to listen on a non-local host without authentication. "
            "Set VANTAGE_V5_AUTH_PASSWORD or VANTAGE_V5_AUTH_USERS_JSON before exposing it, "
            "or set VANTAGE_V5_ALLOW_UNSAFE_PUBLIC_NO_AUTH=true only for a trusted private network."
        )
    account_creation_enabled = auth_enabled
    user_scoped_storage = auth_enabled
    multi_user_enabled = bool(cfg.auth_users)
    session_cookie_name = "vantage_session"
    login_sessions: dict[str, str] = {}
    user_openai_api_keys: dict[str, str] = {}
    durable_scope_cache: dict[str, dict[str, Any]] = {}
    canonical_root = cfg.canonical_root or repo_root / "canonical"
    vault_store = VaultNoteStore(
        vault_root=cfg.nexus_root,
        include_paths=cfg.nexus_include_paths,
        exclude_paths=cfg.nexus_exclude_paths,
    )
    search_service = ConceptSearchService()
    draft_artifact_lifecycle = DraftArtifactLifecycle()
    correction_service = SavedItemCorrectionService()
    local_semantic_actions = LocalSemanticActionEngine(
        draft_artifact_lifecycle=draft_artifact_lifecycle,
    )
    whiteboard_routing = WhiteboardRoutingEngine()
    context_support = ContextSupport(
        whiteboard_routing=whiteboard_routing,
    )
    context_sources = ContextSourceResolver(vault_store=vault_store)

    app = FastAPI(title="Vantage V5", version="0.1.0")
    if cfg.allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=cfg.allowed_hosts)
    web_dir = Path(__file__).resolve().parent / "webapp"
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.middleware("http")
    async def _basic_auth_middleware(request: Request, call_next):
        request.state.user_id = None
        if _is_unsafe_method(request.method) and not _request_origin_allowed(request, cfg.allowed_origins):
            return Response("Cross-origin request blocked.", status_code=403)
        if not auth_enabled:
            if not user_scoped_storage:
                request.state.user_id = cfg.auth_username
            return await call_next(request)

        authorized_user = _request_authorized_user(request)
        public_path = (
            request.url.path == "/"
            or request.url.path == "/api/health"
            or request.url.path == "/api/login"
            or request.url.path == "/api/accounts"
            or request.url.path == "/api/logout"
            or request.url.path.startswith("/static/")
        )
        if authorized_user:
            request.state.user_id = authorized_user
            return await call_next(request)
        if public_path:
            return await call_next(request)
        return JSONResponse({"detail": "Authentication required."}, status_code=401)

    def _request_authorized_user(request: Request) -> str | None:
        basic_user = _basic_auth_authorized_user(
            request.headers.get("authorization"),
            username=cfg.auth_username,
            password=cfg.auth_password,
            users=cfg.auth_users,
        )
        if basic_user:
            return basic_user
        token = str(request.cookies.get(session_cookie_name) or "")
        return login_sessions.get(token)

    def _login_authorized_user(username: str, password: str) -> str | None:
        configured_user = _credentials_authorized_user(
            username,
            password,
            username=cfg.auth_username,
            password=cfg.auth_password,
            users=cfg.auth_users,
        )
        if configured_user:
            return configured_user
        try:
            account_key = _safe_user_storage_id(username)
        except HTTPException:
            return None
        account = _load_account_registry(account_store_path).get(account_key)
        if not account:
            return None
        password_record = account.get("password")
        if not isinstance(password_record, dict):
            return None
        if not _verify_password_record(password, password_record):
            return None
        account_username = str(account.get("username") or "").strip()
        return account_username or account_key

    def _login_response_for_user(user_id: str, *, created: bool = False) -> JSONResponse:
        token = secrets.token_urlsafe(32)
        login_sessions[token] = user_id
        response = JSONResponse(
            {
                "authenticated": True,
                "auth_required": True,
                "multi_user": multi_user_enabled,
                "account_creation_enabled": account_creation_enabled,
                "created": created,
                "user": {"id": user_id},
            },
            status_code=201 if created else 200,
        )
        response.set_cookie(
            session_cookie_name,
            token,
            httponly=True,
            samesite="lax",
            secure=cfg.cookie_secure,
            max_age=60 * 60 * 24 * 14,
        )
        return response

    def _account_key_exists(account_key: str) -> bool:
        if account_key in _load_account_registry(account_store_path):
            return True
        configured_usernames = list(cfg.auth_users.keys())
        if cfg.auth_password:
            configured_usernames.append(cfg.auth_username)
        for username in configured_usernames:
            try:
                if _safe_user_storage_id(username) == account_key:
                    return True
            except HTTPException:
                continue
        return False

    def _scope_key_for_request(request: Request | None) -> str:
        if not user_scoped_storage:
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

    def _canonical_scope() -> dict[str, Any]:
        return {
            "root": canonical_root,
            "concept_store": ConceptStore(canonical_root / "concepts"),
            "memory_store": MemoryStore(canonical_root / "memories"),
            "artifact_store": ArtifactStore(canonical_root / "artifacts"),
        }

    def _durable_scope(request: Request | None = None) -> dict[str, Any]:
        scope_key = _scope_key_for_request(request)
        cached = durable_scope_cache.get(scope_key)
        if cached is not None:
            return cached
        root = _user_root_for_key(scope_key)
        if user_scoped_storage:
            _ensure_storage_root(root)
        canonical_scope = _canonical_scope()
        scope = {
            "user_id": None if scope_key == "__single_user__" else scope_key,
            "root": root,
            "canonical_scope": canonical_scope,
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

    def _scope_key_from_durable_scope(durable_scope: dict[str, Any]) -> str:
        return str(durable_scope.get("user_id") or "__single_user__")

    def _effective_openai_api_key(durable_scope: dict[str, Any]) -> str | None:
        scope_key = _scope_key_from_durable_scope(durable_scope)
        return user_openai_api_keys.get(scope_key) or cfg.openai_api_key

    def _openai_key_status(scope_key: str | None) -> dict[str, Any]:
        user_key = user_openai_api_keys.get(scope_key or "") if scope_key else None
        if user_key:
            return {
                "configured": True,
                "source": "user",
                "masked_key": _mask_openai_api_key(user_key),
                "environment_configured": bool(cfg.openai_api_key),
            }
        if cfg.openai_api_key:
            return {
                "configured": True,
                "source": "environment",
                "masked_key": _mask_openai_api_key(cfg.openai_api_key),
                "environment_configured": True,
            }
        return {
            "configured": False,
            "source": "none",
            "masked_key": "",
            "environment_configured": False,
        }

    def _openai_key_status_for_request(request: Request) -> dict[str, Any]:
        user_id = str(getattr(request.state, "user_id", "") or "")
        if user_scoped_storage and not user_id:
            return _openai_key_status(None)
        return _openai_key_status(_scope_key_for_request(request))

    def _protocol_engine_for_scope(durable_scope: dict[str, Any]) -> ProtocolEngine:
        return ProtocolEngine(
            model=cfg.model,
            openai_api_key=_effective_openai_api_key(durable_scope),
        )

    def _runtime(durable_scope: dict[str, Any], session: ExperimentSession | None) -> dict[str, Any]:
        canonical_scope = durable_scope["canonical_scope"]
        if session is None:
            concept_store = durable_scope["concept_store"]
            memory_store = durable_scope["memory_store"]
            memory_trace_store = durable_scope["memory_trace_store"]
            artifact_store = durable_scope["artifact_store"]
            workspace_store = durable_scope["workspace_store"]
            state_store = durable_scope["state_store"]
            reference_concept_store = canonical_scope["concept_store"]
            reference_memory_store = canonical_scope["memory_store"]
            reference_memory_trace_store = None
            reference_artifact_store = canonical_scope["artifact_store"]
            traces_dir = durable_scope["traces_dir"]
            scope = "durable"
        else:
            concept_store = ConceptStore(session.concepts_dir)
            memory_store = MemoryStore(session.memories_dir)
            memory_trace_store = MemoryTraceStore(session.memory_trace_dir)
            artifact_store = ArtifactStore(session.artifacts_dir)
            workspace_store = WorkspaceStore(session.workspaces_dir)
            state_store = ActiveWorkspaceStateStore(session.state_path)
            reference_concept_store = ConceptOverlayStore(
                durable_scope["concept_store"],
                canonical_scope["concept_store"],
            )
            reference_memory_store = MemoryOverlayStore(
                durable_scope["memory_store"],
                canonical_scope["memory_store"],
            )
            reference_memory_trace_store = None
            reference_artifact_store = ArtifactOverlayStore(
                durable_scope["artifact_store"],
                canonical_scope["artifact_store"],
            )
            traces_dir = session.traces_dir
            scope = "experiment"
        openai_api_key = _effective_openai_api_key(durable_scope)
        vetting_service = ConceptVettingService(
            model=cfg.model,
            openai_api_key=openai_api_key,
        )
        meta_service = MetaService(
            model=cfg.model,
            openai_api_key=openai_api_key,
        )
        protocol_engine = ProtocolEngine(
            model=cfg.model,
            openai_api_key=openai_api_key,
        )
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
            openai_api_key=openai_api_key,
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
            openai_api_key=openai_api_key,
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
            "reference_concept_store": reference_concept_store,
            "reference_memory_store": reference_memory_store,
            "reference_artifact_store": reference_artifact_store,
            "executor": executor,
            "chat_service": chat_service,
            "scenario_lab_service": scenario_lab_service,
            "scope": scope,
        }

    def _saved_note_cards(durable_scope: dict[str, Any], session: ExperimentSession | None) -> list[dict[str, Any]]:
        return [
            _serialize_saved_note_card(record, scope=_record_scope(record, session))
            for record in _saved_note_records(durable_scope, session)
        ]

    def _concept_records(durable_scope: dict[str, Any], session: ExperimentSession | None) -> list[Any]:
        canonical_scope = durable_scope["canonical_scope"]
        if session is None:
            return overlay_records(
                durable_scope["concept_store"].list_concepts(),
                canonical_scope["concept_store"].list_concepts(),
            )
        return overlay_records(
            ConceptStore(session.concepts_dir).list_concepts(),
            durable_scope["concept_store"].list_concepts(),
            canonical_scope["concept_store"].list_concepts(),
        )

    def _record_scope(record: Any, session: ExperimentSession | None) -> str:
        if "canonical" in record.path.parts:
            return "canonical"
        return "experiment" if session and "experiments" in record.path.parts else "durable"

    def _serialize_protocol_catalog_entry(entry: Any, session: ExperimentSession | None) -> dict[str, Any]:
        if entry.record is not None:
            return _serialize_concept_card(entry.record, scope=_record_scope(entry.record, session))
        if entry.built_in_kind is None:
            raise HTTPException(status_code=500, detail="Protocol catalog entry is incomplete.")
        return _serialize_built_in_protocol(entry.built_in_kind)

    def _saved_note_records(durable_scope: dict[str, Any], session: ExperimentSession | None) -> list[Any]:
        canonical_scope = durable_scope["canonical_scope"]
        if session is None:
            return overlay_records(
                durable_scope["memory_store"].list_memories(),
                durable_scope["artifact_store"].list_artifacts(),
                canonical_scope["memory_store"].list_memories(),
                canonical_scope["artifact_store"].list_artifacts(),
            )
        return overlay_records(
            MemoryStore(session.memories_dir).list_memories(),
            ArtifactStore(session.artifacts_dir).list_artifacts(),
            durable_scope["memory_store"].list_memories(),
            durable_scope["artifact_store"].list_artifacts(),
            canonical_scope["memory_store"].list_memories(),
            canonical_scope["artifact_store"].list_artifacts(),
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
        openai_api_key = _effective_openai_api_key(durable_scope)
        turn_orchestrator = TurnOrchestrator(
            navigator_service=NavigatorService(
                model=cfg.model,
                openai_api_key=openai_api_key,
            ),
            context_engine=context_engine,
            protocol_engine=ProtocolEngine(
                model=cfg.model,
                openai_api_key=openai_api_key,
            ),
            local_semantic_actions=local_semantic_actions,
            whiteboard_routing=whiteboard_routing,
            hooks=TurnOrchestratorHooks(
                should_enter_scenario_lab=_should_enter_scenario_lab,
            ),
        )
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
        openai_key_status = _openai_key_status_for_request(request)
        if user_scoped_storage:
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
            "mode": "openai" if openai_key_status["configured"] else "fallback",
            "openai_key": openai_key_status,
            "workspace_id": workspace_id,
            "nexus_enabled": vault_store.is_enabled(),
            "experiment": experiment,
            "multi_user": multi_user_enabled,
            "auth_required": auth_enabled,
            "authenticated": bool(user_id) or not auth_enabled,
            "account_creation_enabled": account_creation_enabled,
            "user": {"id": user_id} if user_id else None,
        }

    @app.post("/api/login")
    def login(request: LoginRequest) -> JSONResponse:
        if not auth_enabled:
            return JSONResponse(
                {
                    "authenticated": True,
                    "auth_required": False,
                    "multi_user": multi_user_enabled,
                    "account_creation_enabled": False,
                    "user": {"id": cfg.auth_username},
                }
            )
        authorized_user = _login_authorized_user(request.username, request.password)
        if not authorized_user:
            raise HTTPException(status_code=401, detail="Invalid username or password.")
        return _login_response_for_user(authorized_user)

    @app.post("/api/accounts")
    def create_account(request: CreateAccountRequest) -> JSONResponse:
        if not account_creation_enabled:
            raise HTTPException(status_code=404, detail="Account creation is not enabled.")
        username = _normalize_account_username(request.username)
        account_key = _safe_user_storage_id(username)
        if _account_key_exists(account_key):
            raise HTTPException(status_code=409, detail="An account with that username already exists.")
        accounts = _load_account_registry(account_store_path)
        accounts[account_key] = {
            "username": username,
            "created_at": datetime.now(UTC).isoformat(),
            "password": _make_password_record(request.password),
        }
        _write_account_registry(account_store_path, accounts)
        _ensure_storage_root(_user_root_for_key(account_key))
        durable_scope_cache.pop(account_key, None)
        return _login_response_for_user(username, created=True)

    @app.post("/api/logout")
    def logout(request: Request) -> JSONResponse:
        token = str(request.cookies.get(session_cookie_name) or "")
        if token:
            login_sessions.pop(token, None)
        response = JSONResponse({"authenticated": False})
        response.delete_cookie(session_cookie_name, secure=cfg.cookie_secure, samesite="lax")
        return response

    @app.get("/api/openai-key")
    def get_openai_key_status(request: Request) -> dict[str, Any]:
        status = _openai_key_status(_scope_key_for_request(request))
        return {
            "mode": "openai" if status["configured"] else "fallback",
            "openai_key": status,
        }

    @app.put("/api/openai-key")
    def put_openai_key(request: OpenAIKeyRequest, http_request: Request) -> dict[str, Any]:
        api_key = request.api_key.strip()
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key is required.")
        scope_key = _scope_key_for_request(http_request)
        user_openai_api_keys[scope_key] = api_key
        status = _openai_key_status(scope_key)
        return {
            "mode": "openai",
            "openai_key": status,
        }

    @app.delete("/api/openai-key")
    def delete_openai_key(request: Request) -> dict[str, Any]:
        scope_key = _scope_key_for_request(request)
        user_openai_api_keys.pop(scope_key, None)
        status = _openai_key_status(scope_key)
        return {
            "mode": "openai" if status["configured"] else "fallback",
            "openai_key": status,
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
        protocol_engine = _protocol_engine_for_scope(durable_scope)
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
        protocol_engine = _protocol_engine_for_scope(durable_scope)
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
        protocol_engine = _protocol_engine_for_scope(durable_scope)
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

    @app.post("/api/records/{source}/{record_id}/corrections")
    def correct_record(
        source: str,
        record_id: str,
        request: RecordCorrectionRequest,
        http_request: Request,
    ) -> dict[str, Any]:
        durable_scope = _durable_scope(http_request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        try:
            correction = correction_service.apply(
                source=source,
                record_id=record_id,
                action=request.action,
                reason=request.reason,
                scope=request.scope,
                durable_scope=durable_scope,
                runtime=runtime,
                has_active_experiment=session is not None,
            )
        except CorrectionRejected as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"correction": correction.to_dict()}

    @app.get("/api/memory/{memory_id}")
    def get_memory_item(memory_id: str, request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        session = durable_scope["experiment_manager"].get_active_session()
        runtime = _runtime(durable_scope, session)
        for stores in [
            (runtime["memory_store"], runtime.get("reference_memory_store")),
            (runtime["artifact_store"], runtime.get("reference_artifact_store")),
        ]:
            try:
                note = get_overlay_record(memory_id, *stores)
                item = _serialize_saved_note_card(note, scope=_record_scope(note, session))
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
            concept = get_overlay_record(
                concept_id,
                runtime["concept_store"],
                runtime.get("reference_concept_store"),
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _serialize_concept_card(concept, scope=_record_scope(concept, session))

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
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    return _credentials_authorized_user(
        supplied_username,
        supplied_password,
        username=username,
        password=password,
        users=users,
    )


def _credentials_authorized_user(
    supplied_username: str,
    supplied_password: str,
    *,
    username: str,
    password: str | None,
    users: dict[str, str] | None = None,
) -> str | None:
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


def _normalize_account_username(username: str) -> str:
    normalized = username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,80}", normalized):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-80 characters and use only letters, numbers, dots, underscores, or hyphens.",
        )
    return normalized


def _load_account_registry(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.exception("Could not read Vantage account registry.")
        return {}
    accounts = payload.get("accounts") if isinstance(payload, dict) else None
    if not isinstance(accounts, dict):
        return {}
    return {
        str(account_key): account
        for account_key, account in accounts.items()
        if isinstance(account, dict)
    }


def _write_account_registry(path: Path, accounts: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "accounts": accounts,
    }
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary_path.replace(path)


def _make_password_record(password: str) -> dict[str, Any]:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        ACCOUNT_PASSWORD_ITERATIONS,
    ).hex()
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": ACCOUNT_PASSWORD_ITERATIONS,
        "salt": salt,
        "hash": password_hash,
    }


def _verify_password_record(password: str, record: dict[str, Any]) -> bool:
    if record.get("algorithm") != "pbkdf2_sha256":
        return False
    try:
        iterations = int(record.get("iterations") or 0)
        salt = str(record.get("salt") or "")
        expected_hash = str(record.get("hash") or "")
    except (TypeError, ValueError):
        return False
    if iterations <= 0 or not salt or not expected_hash:
        return False
    supplied_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        iterations,
    ).hex()
    return secrets.compare_digest(supplied_hash, expected_hash)


def _mask_openai_api_key(api_key: str) -> str:
    normalized = api_key.strip()
    if not normalized:
        return ""
    if len(normalized) <= 8:
        return "***"
    return f"{normalized[:4]}...{normalized[-4:]}"


def _requires_public_auth(host: str) -> bool:
    normalized = str(host or "").strip().lower()
    if normalized in {"", "localhost", "127.0.0.1", "::1"}:
        return False
    if normalized in {"0.0.0.0", "::", "*"}:
        return True
    try:
        parsed = ip_address(normalized)
    except ValueError:
        return True
    return not parsed.is_loopback


def _is_unsafe_method(method: str) -> bool:
    return method.upper() not in {"GET", "HEAD", "OPTIONS", "TRACE"}


def _request_origin_allowed(request: Request, allowed_origins: list[str]) -> bool:
    origin = str(request.headers.get("origin") or "").strip()
    if not origin:
        referer = str(request.headers.get("referer") or "").strip()
        if not referer:
            return True
        origin = _origin_from_url(referer)
    if not origin:
        return True
    normalized_origin = _normalize_origin(origin)
    if normalized_origin in {_normalize_origin(allowed) for allowed in allowed_origins}:
        return True
    origin_host = _host_port_from_origin(normalized_origin)
    request_host = _host_port_from_host_header(str(request.headers.get("host") or ""))
    return bool(origin_host and request_host and origin_host == request_host)


def _origin_from_url(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _normalize_origin(value: str) -> str:
    parsed = urlparse(value.strip())
    if not parsed.scheme or not parsed.netloc:
        return value.strip().rstrip("/")
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    default_port = 443 if scheme == "https" else 80 if scheme == "http" else None
    if port is None or port == default_port:
        return f"{scheme}://{hostname}"
    return f"{scheme}://{hostname}:{port}"


def _host_port_from_origin(origin: str) -> str:
    parsed = urlparse(origin)
    if not parsed.hostname:
        return ""
    port = parsed.port
    return f"{parsed.hostname.lower()}:{port}" if port else parsed.hostname.lower()


def _host_port_from_host_header(host: str) -> str:
    normalized = host.strip().lower()
    if not normalized:
        return ""
    if normalized.startswith("["):
        end = normalized.find("]")
        if end == -1:
            return normalized
        hostname = normalized[1:end]
        port = normalized[end + 2 :] if normalized[end + 1 : end + 2] == ":" else ""
        return f"{hostname}:{port}" if port else hostname
    if ":" in normalized:
        hostname, port = normalized.rsplit(":", 1)
        return f"{hostname}:{port}" if port else hostname
    return normalized


def _should_enter_scenario_lab(decision: NavigationDecision) -> bool:
    return decision.mode == "scenario_lab" and decision.confidence >= SCENARIO_LAB_MIN_CONFIDENCE
