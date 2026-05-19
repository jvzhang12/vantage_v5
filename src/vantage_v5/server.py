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
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from vantage_v5.config import AppConfig
from vantage_v5.services.artifact_actions import action_graph_payload
from vantage_v5.services.artifact_actions import action_surface_context
from vantage_v5.services.artifact_actions import ArtifactActionPlan
from vantage_v5.services.artifact_actions import ArtifactActionPlanner
from vantage_v5.services.artifact_actions import ArtifactActionStore
from vantage_v5.services.artifact_actions import execute_artifact_action
from vantage_v5.services.artifact_actions import reject_artifact_action
from vantage_v5.services.artifact_mutation_compiler import ArtifactMutationCompiler
from vantage_v5.services.attention import AttentionEngine
from vantage_v5.services.calendar import LocalCalendarProvider
from vantage_v5.services.calendar import resolve_calendar_date
from vantage_v5.services.capabilities import build_app_capability_manifest
from vantage_v5.services.chat import ChatService
from vantage_v5.services.chat import persist_final_chat_response_trace
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
from vantage_v5.services.model_client import codex_oauth_status
from vantage_v5.services.model_client import MODEL_PROVIDER_CODEX_OAUTH
from vantage_v5.services.model_client import MODEL_PROVIDER_OPENAI
from vantage_v5.services.model_client import ModelClientConfig
from vantage_v5.services.model_client import normalize_model_provider
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
from vantage_v5.services.surface_payloads import SurfacePayloadBuilder
from vantage_v5.services.surface_payloads import SurfacePayloadResult
from vantage_v5.services.surface_payloads import surface_assistant_message
from vantage_v5.services.tasks import LocalTaskProvider
from vantage_v5.services.turn_plan import build_turn_plan_surface_authority
from vantage_v5.services.turn_plan import build_turn_plan_operational_proposal_authority
from vantage_v5.services.turn_plan import project_write_intent_compatibility
from vantage_v5.services.turn_payloads import attach_safe_turn_state
from vantage_v5.services.turn_orchestrator import TurnOrchestrator
from vantage_v5.services.turn_orchestrator import TurnOrchestratorHooks
from vantage_v5.services.vetting import ConceptVettingService
from vantage_v5.services.vector_index import SQLiteVectorIndex
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
PWA_ICON_FILES = frozenset(
    {
        "apple-touch-icon.png",
        "vantage-icon-192.png",
        "vantage-icon-512.png",
        "vantage-icon.svg",
    }
)


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)
    workspace_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("workspace_id", "workspaceId"),
    )
    workspace_scope: str = Field(
        default="auto",
        validation_alias=AliasChoices("workspace_scope", "workspaceScope"),
    )
    workspace_content: str | None = Field(
        default=None,
        validation_alias=AliasChoices("workspace_content", "workspaceContent"),
    )
    whiteboard_mode: str = Field(
        default="auto",
        validation_alias=AliasChoices("whiteboard_mode", "whiteboardMode"),
    )
    pinned_context_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("pinned_context_id", "pinnedContextId"),
    )
    selected_record_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("selected_record_id", "selectedRecordId"),
    )
    memory_intent: str = Field(
        default="auto",
        validation_alias=AliasChoices("memory_intent", "memoryIntent"),
    )
    pending_workspace_update: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("pending_workspace_update", "pendingWorkspaceUpdate"),
    )
    visible_artifacts: list[dict[str, Any]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("visible_artifacts", "visibleArtifacts"),
    )


class WhiteboardAcceptRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    history: list[dict[str, str]] = Field(default_factory=list)
    workspace_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("workspace_id", "workspaceId"),
    )
    workspace_scope: str = Field(
        default="auto",
        validation_alias=AliasChoices("workspace_scope", "workspaceScope"),
    )
    workspace_content: str | None = Field(
        default=None,
        validation_alias=AliasChoices("workspace_content", "workspaceContent"),
    )
    pinned_context_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("pinned_context_id", "pinnedContextId"),
    )
    selected_record_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("selected_record_id", "selectedRecordId"),
    )
    memory_intent: str = Field(
        default="auto",
        validation_alias=AliasChoices("memory_intent", "memoryIntent"),
    )
    pending_workspace_update: dict[str, Any] = Field(
        validation_alias=AliasChoices("pending_workspace_update", "pendingWorkspaceUpdate"),
    )


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
    access_code: str | None = Field(default=None, max_length=4096)


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
    auth_enabled = bool(cfg.auth_password or cfg.auth_users or cfg.account_creation_code or account_store_path.exists())
    if _requires_public_auth(cfg.host) and not auth_enabled and not cfg.allow_unsafe_public_no_auth:
        raise RuntimeError(
            "Vantage is configured to listen on a non-local host without authentication. "
            "Set VANTAGE_V5_AUTH_PASSWORD, VANTAGE_V5_AUTH_USERS_JSON, or VANTAGE_V5_ACCOUNT_CREATION_CODE before exposing it, "
            "or set VANTAGE_V5_ALLOW_UNSAFE_PUBLIC_NO_AUTH=true only for a trusted private network."
        )
    account_creation_enabled = auth_enabled
    account_creation_code_required = bool(cfg.account_creation_code)
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
    configured_calendar_events_path = _resolve_repo_path(
        repo_root,
        cfg.calendar_events_path,
        default_relative="state/calendar/events.json",
    )
    configured_tasks_path = _resolve_repo_path(
        repo_root,
        cfg.tasks_path,
        default_relative="state/tasks/tasks.json",
    )

    app = FastAPI(title="Vantage V5", version="0.1.0")
    if cfg.allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=cfg.allowed_hosts)
    package_dir = Path(__file__).resolve().parent
    web_dir = package_dir / "webapp"
    pwa_public_dir = package_dir / "webapp_react" / "public"
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
            or request.url.path == "/manifest.webmanifest"
            or request.url.path == "/sw.js"
            or request.url.path.startswith("/icons/")
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
                "account_creation_code_required": account_creation_code_required,
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
        for folder in [
            "concepts",
            "memories",
            "memory_trace",
            "artifacts",
            "workspaces",
            "state",
            "state/artifact_actions",
            "state/calendar",
            "state/tasks",
            "traces",
        ]:
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

    def _seed_account_calendar_file(root: Path) -> None:
        if cfg.calendar_events_path:
            return
        events_path = root / "state" / "calendar" / "events.json"
        if events_path.exists():
            return
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text(
            json.dumps(
                {
                    "calendars": [{"id": "local", "title": "Calendar"}],
                    "events": [],
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
            "artifact_action_store": ArtifactActionStore(root / "state" / "artifact_actions"),
            "experiment_manager": ExperimentSessionManager(root / "state"),
            "traces_dir": root / "traces",
        }
        durable_scope_cache[scope_key] = scope
        return scope

    def _calendar_provider_for_scope(durable_scope: dict[str, Any]) -> LocalCalendarProvider:
        if cfg.calendar_events_path:
            events_path = configured_calendar_events_path
        else:
            events_path = Path(durable_scope["root"]) / "state" / "calendar" / "events.json"
        writable = bool(durable_scope.get("user_id")) and not cfg.calendar_events_path
        return LocalCalendarProvider(events_path=events_path, writable=writable)

    def _task_provider_for_scope(durable_scope: dict[str, Any]) -> LocalTaskProvider:
        if cfg.tasks_path:
            tasks_path = configured_tasks_path
        else:
            tasks_path = Path(durable_scope["root"]) / "state" / "tasks" / "tasks.json"
        writable = bool(durable_scope.get("user_id")) and not cfg.tasks_path
        return LocalTaskProvider(tasks_path=tasks_path, writable=writable)

    def _surface_payload_builder_for_scope(durable_scope: dict[str, Any]) -> SurfacePayloadBuilder:
        return SurfacePayloadBuilder(
            calendar_provider=_calendar_provider_for_scope(durable_scope),
            task_provider=_task_provider_for_scope(durable_scope),
        )

    def _artifact_action_store_for_scope(durable_scope: dict[str, Any]) -> ArtifactActionStore:
        store = durable_scope.get("artifact_action_store")
        if isinstance(store, ArtifactActionStore):
            return store
        return ArtifactActionStore(Path(durable_scope["root"]) / "state" / "artifact_actions")

    def _artifact_action_planner_for_scope(durable_scope: dict[str, Any]) -> ArtifactActionPlanner:
        return ArtifactActionPlanner(
            calendar_provider=_calendar_provider_for_scope(durable_scope),
            task_provider=_task_provider_for_scope(durable_scope),
            action_store=_artifact_action_store_for_scope(durable_scope),
        )

    def _artifact_mutation_compiler_for_scope(
        durable_scope: dict[str, Any],
        *,
        app_capabilities: dict[str, Any],
    ) -> ArtifactMutationCompiler:
        return ArtifactMutationCompiler(
            planner=_artifact_action_planner_for_scope(durable_scope),
            app_capabilities=app_capabilities,
            model=cfg.model,
            model_client_config=_model_client_config(durable_scope),
        )

    def _app_capability_manifest_for_scope(
        durable_scope: dict[str, Any],
        *,
        workspace_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return build_app_capability_manifest(
            calendar_source=_calendar_provider_for_scope(durable_scope).source_status(),
            task_source=_task_provider_for_scope(durable_scope).source_status(),
            workspace=workspace_payload,
        )

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

    def _model_client_config(durable_scope: dict[str, Any]) -> ModelClientConfig:
        return ModelClientConfig(
            provider=cfg.model_provider,
            openai_api_key=_effective_openai_api_key(durable_scope),
            codex_auth_path=cfg.codex_auth_path,
            codex_base_url=cfg.codex_base_url,
        )

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

    def _model_auth_status(scope_key: str | None) -> dict[str, Any]:
        provider = normalize_model_provider(cfg.model_provider)
        if provider == MODEL_PROVIDER_CODEX_OAUTH:
            codex_status = codex_oauth_status(cfg.codex_auth_path)
            configured = bool(codex_status["configured"])
            return {
                "configured": configured,
                "provider": MODEL_PROVIDER_CODEX_OAUTH,
                "mode": MODEL_PROVIDER_CODEX_OAUTH if configured else "fallback",
                "label": "Codex OAuth",
                "detail": codex_status["detail"],
                "codex_oauth": codex_status,
                "openai_key": _openai_key_status(scope_key),
            }
        openai_status = _openai_key_status(scope_key)
        configured = bool(openai_status["configured"])
        return {
            "configured": configured,
            "provider": MODEL_PROVIDER_OPENAI,
            "mode": "openai" if configured else "fallback",
            "label": "OpenAI API key",
            "detail": _model_auth_openai_detail(openai_status),
            "codex_oauth": codex_oauth_status(cfg.codex_auth_path),
            "openai_key": openai_status,
        }

    def _model_auth_status_for_request(request: Request) -> dict[str, Any]:
        user_id = str(getattr(request.state, "user_id", "") or "")
        if user_scoped_storage and not user_id:
            return _model_auth_status(None)
        return _model_auth_status(_scope_key_for_request(request))

    def _protocol_engine_for_scope(durable_scope: dict[str, Any]) -> ProtocolEngine:
        return ProtocolEngine(
            model=cfg.model,
            openai_api_key=_effective_openai_api_key(durable_scope),
            model_client_config=_model_client_config(durable_scope),
            canonical_root=Path(durable_scope["canonical_scope"]["root"]),
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
        model_client_config = _model_client_config(durable_scope)
        vetting_service = ConceptVettingService(
            model=cfg.model,
            openai_api_key=openai_api_key,
            model_client_config=model_client_config,
        )
        meta_service = MetaService(
            model=cfg.model,
            openai_api_key=openai_api_key,
            model_client_config=model_client_config,
        )
        protocol_engine = ProtocolEngine(
            model=cfg.model,
            openai_api_key=openai_api_key,
            model_client_config=model_client_config,
            canonical_root=Path(canonical_scope["root"]),
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
            canonical_root=Path(canonical_scope["root"]),
            experiment_root=session.root if session is not None else None,
            runtime_scope=scope,
        )
        chat_service = ChatService(
            model=cfg.model,
            openai_api_key=openai_api_key,
            model_client_config=model_client_config,
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
            runtime_scope=scope,
            canonical_root=Path(canonical_scope["root"]),
            experiment_root=session.root if session is not None else None,
        )
        scenario_lab_service = ScenarioLabService(
            model=cfg.model,
            openai_api_key=openai_api_key,
            model_client_config=model_client_config,
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
            runtime_scope=scope,
            canonical_root=Path(canonical_scope["root"]),
            experiment_root=session.root if session is not None else None,
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
            "canonical_root": Path(canonical_scope["root"]),
            "experiment_root": session.root if session is not None else None,
        }

    def _saved_note_cards(durable_scope: dict[str, Any], session: ExperimentSession | None) -> list[dict[str, Any]]:
        return [
            _serialize_saved_note_card(record, scope=_record_scope(record, durable_scope, session))
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

    def _record_scope(record: Any, durable_scope: dict[str, Any], session: ExperimentSession | None) -> str:
        path = getattr(record, "path", None)
        if _path_is_relative_to(path, Path(durable_scope["canonical_scope"]["root"])):
            return "canonical"
        if session is not None and _path_is_relative_to(path, session.root):
            return "experiment"
        return "durable"

    def _path_is_relative_to(path: Any, root: Path | None) -> bool:
        if path is None or root is None:
            return False
        try:
            Path(path).resolve().relative_to(root.resolve())
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def _serialize_protocol_catalog_entry(
        entry: Any,
        durable_scope: dict[str, Any],
        session: ExperimentSession | None,
    ) -> dict[str, Any]:
        if entry.record is not None:
            return _serialize_concept_card(entry.record, scope=_record_scope(entry.record, durable_scope, session))
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
        visible_artifacts: list[dict[str, Any]] | None = None,
        navigation: NavigationDecision | None = None,
        force_pending_workspace_update: bool = False,
    ) -> dict[str, Any]:
        openai_api_key = _effective_openai_api_key(durable_scope)
        model_client_config = _model_client_config(durable_scope)
        turn_orchestrator = TurnOrchestrator(
            navigator_service=NavigatorService(
                model=cfg.model,
                openai_api_key=openai_api_key,
                model_client_config=model_client_config,
            ),
            context_engine=context_engine,
            protocol_engine=ProtocolEngine(
                model=cfg.model,
                openai_api_key=openai_api_key,
                model_client_config=model_client_config,
                canonical_root=Path(durable_scope["canonical_scope"]["root"]),
            ),
            local_semantic_actions=local_semantic_actions,
            whiteboard_routing=whiteboard_routing,
            hooks=TurnOrchestratorHooks(
                should_enter_scenario_lab=_should_enter_scenario_lab,
            ),
            attention_engine=AttentionEngine(
                calendar_provider=_calendar_provider_for_scope(durable_scope),
                task_provider=_task_provider_for_scope(durable_scope),
                vector_index=SQLiteVectorIndex(Path(durable_scope["root"]) / "state" / "vector_index.sqlite3"),
            ),
        )
        app_capabilities = _app_capability_manifest_for_scope(durable_scope)
        payload = turn_orchestrator.run(
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
                visible_artifacts=visible_artifacts,
                navigation=navigation,
                force_pending_workspace_update=force_pending_workspace_update,
                app_capabilities=app_capabilities,
            )
        )
        surface_authority = build_turn_plan_surface_authority(
            response_payload=payload,
            request_payload={"message": message, "memory_intent": memory_intent},
        )
        action_visible_artifacts = [
            *(visible_artifacts or []),
            *_visible_artifacts_from_selected_attention(payload.get("selected_attention_resources")),
        ]
        action_plan = ArtifactActionPlan(artifact_actions=[])
        turn_plan_request_payload = {"message": message, "memory_intent": memory_intent}
        if not surface_authority.blocks_artifact_actions:
            artifact_mutation_compiler = _artifact_mutation_compiler_for_scope(
                durable_scope,
                app_capabilities=app_capabilities,
            )
            candidate_plan = artifact_mutation_compiler.compile_for_turn(
                user_message=message,
                semantic_action=str(payload.get("assistant_message") or ""),
                visible_artifacts=action_visible_artifacts,
                persist=False,
            )
            if candidate_plan.artifact_actions:
                candidate_payload = {
                    **payload,
                    "artifact_actions": candidate_plan.artifact_actions,
                    "surface_invocation": _artifact_action_surface_invocation_payload(
                        candidate_plan.artifact_actions[0],
                        existing=payload.get("surface_invocation"),
                    ),
                }
                proposal_authority = build_turn_plan_operational_proposal_authority(
                    response_payload=candidate_payload,
                    request_payload=turn_plan_request_payload,
                )
                payload["operational_proposal_authority"] = proposal_authority.to_dict()
                if proposal_authority.allowed:
                    action_plan = artifact_mutation_compiler.persist_plan(candidate_plan)
                else:
                    action_plan = ArtifactActionPlan(artifact_actions=[])
            else:
                action_plan = candidate_plan
        payload["artifact_actions"] = action_plan.artifact_actions
        if action_plan.artifact_actions:
            if _workspace_update_is_whiteboard_offer(payload.get("workspace_update")):
                payload["workspace_update"] = None
            payload["surface_invocation"] = _artifact_action_surface_invocation_payload(
                action_plan.artifact_actions[0],
                existing=payload.get("surface_invocation"),
            )
            proposal_authority = build_turn_plan_operational_proposal_authority(
                response_payload=payload,
                request_payload=turn_plan_request_payload,
            )
            payload["operational_proposal_authority"] = proposal_authority.to_dict()
        surface_authority = build_turn_plan_surface_authority(
            response_payload=payload,
            request_payload={"message": message, "memory_intent": memory_intent},
        )
        if surface_authority.surface_payload_policy == "build_operational_payload":
            surface_result = _surface_payload_builder_for_scope(durable_scope).build_for_turn(
                message=message,
                surface_invocation=surface_authority.surface_invocation,
            )
        else:
            surface_result = SurfacePayloadResult(surface_payloads=[], active_surface_id=None)
        payload.update(surface_result.to_dict())
        surface_message = surface_assistant_message(surface_result.surface_payloads)
        if surface_message and not isinstance(payload.get("workspace_update"), dict) and not action_plan.assistant_message:
            payload["assistant_message"] = surface_message
        if action_plan.assistant_message:
            payload["assistant_message"] = action_plan.assistant_message
        payload["app_capabilities"] = _app_capability_manifest_for_scope(
            durable_scope,
            workspace_payload=payload.get("workspace") if isinstance(payload.get("workspace"), dict) else None,
        )
        payload = project_write_intent_compatibility(
            response_payload=payload,
            request_payload={"message": message, "memory_intent": memory_intent},
        )
        trace_path = payload.pop("_turn_trace_path", None)
        final_payload = attach_safe_turn_state(payload)
        try:
            persist_final_chat_response_trace(
                traces_dir=_final_response_trace_dir(durable_scope, final_payload),
                trace_path=trace_path,
                request_payload=_chat_final_trace_request_payload(
                    message=message,
                    history=history,
                    workspace_id=workspace_id,
                    workspace_scope=workspace_scope,
                    workspace_content=workspace_content,
                    whiteboard_mode=whiteboard_mode,
                    pinned_context_id=pinned_context_id,
                    memory_intent=memory_intent,
                    pending_workspace_update=pending_workspace_update,
                    visible_artifacts=visible_artifacts,
                    force_pending_workspace_update=force_pending_workspace_update,
                ),
                response_payload=final_payload,
            )
        except Exception:
            logger.exception("Failed to persist final chat response trace.")
        return final_payload

    def _final_response_trace_dir(durable_scope: dict[str, Any], payload: dict[str, Any]) -> Path:
        experiment = payload.get("experiment") if isinstance(payload.get("experiment"), dict) else {}
        if experiment.get("active"):
            session = durable_scope["experiment_manager"].get_active_session()
            if session is not None:
                return session.traces_dir
        return Path(durable_scope["traces_dir"])

    def _chat_final_trace_request_payload(
        *,
        message: str,
        history: list[dict[str, str]],
        workspace_id: str | None,
        workspace_scope: str,
        workspace_content: str | None,
        whiteboard_mode: str,
        pinned_context_id: str | None,
        memory_intent: str,
        pending_workspace_update: dict[str, Any] | None,
        visible_artifacts: list[dict[str, Any]] | None,
        force_pending_workspace_update: bool,
    ) -> dict[str, Any]:
        return {
            "message": message,
            "user_message": message,
            "history": history[-6:],
            "workspace_id": workspace_id,
            "workspace_scope": workspace_scope,
            "workspace_content_supplied": workspace_content is not None,
            "whiteboard_mode": whiteboard_mode,
            "pinned_context_id": pinned_context_id,
            "memory_intent": memory_intent,
            "pending_workspace_update": pending_workspace_update,
            "visible_artifacts": visible_artifacts or [],
            "force_pending_workspace_update": force_pending_workspace_update,
        }

    def _visible_artifacts_from_selected_attention(value: Any) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        if not isinstance(value, list):
            return artifacts
        for item in value:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("suggested_surface") or item.get("kind") or "").strip()
            if kind not in {"today_briefing", "calendar_day", "calendar_week", "task_focus", "whiteboard"}:
                continue
            artifacts.append(
                {
                    "id": item.get("resource_id") or item.get("id"),
                    "kind": kind,
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "content": item.get("content"),
                    "data": item.get("data") if isinstance(item.get("data"), dict) else {},
                    "source_refs": [
                        {
                            "id": item.get("resource_id") or item.get("id"),
                            "title": item.get("title"),
                            "source": item.get("source"),
                            "kind": item.get("kind"),
                        }
                    ],
                }
            )
        return artifacts

    def _workspace_update_is_whiteboard_offer(value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        return str(value.get("type") or value.get("status") or value.get("proposal_kind") or "").strip() in {
            "offer_whiteboard",
            "offered",
            "offer",
        }

    def _artifact_action_surface_invocation_payload(
        action: dict[str, Any],
        *,
        existing: Any,
    ) -> dict[str, Any]:
        context = action_surface_context(action)
        artifact_kind = str(action.get("artifact_kind") or "artifact")
        context_kind = str(context.get("kind") or ("task_focus" if artifact_kind == "task" else "calendar_day"))
        if context_kind == "calendar_week":
            primary_surface = "calendar_week"
        elif context_kind == "task_focus" or artifact_kind == "task":
            primary_surface = "task_focus"
        else:
            primary_surface = "calendar_day"
        existing_payload = existing if isinstance(existing, dict) else {}
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        capture = payload.get("capture") if isinstance(payload.get("capture"), dict) else {}
        capture_reason = str(capture.get("reason") or "").strip()
        action_reason = capture_reason or (
            "The user asked to change a visible calendar artifact."
            if artifact_kind == "calendar"
            else "The user stated a concrete task or artifact update."
        )
        return {
            **existing_payload,
            "policy_version": "artifact-action-v1",
            "intent": f"{artifact_kind}_mutation" if not capture else f"{artifact_kind}_capture",
            "primary_surface": primary_surface,
            "supporting_surfaces": [],
            "surfaces": [
                {
                    "kind": context_kind if context_kind in {"today_briefing", "calendar_week", "calendar_day", "task_focus"} else primary_surface,
                    "role": "target",
                    "reason": action_reason,
                    "status": "already_open" if context.get("id") else "selected",
                }
            ],
            "write_behavior": "proposal_only",
            "reason": f"{artifact_kind.title()} edits require confirmation before Vantage mutates the user-scoped local store.",
            "confidence": float(capture.get("confidence") or 0.9),
            "data_sources": [source for source in ["visible_artifact" if context.get("id") else "", artifact_kind] if source],
            "trigger": "artifact_action_policy",
            "requires_confirmation": True,
            "capability_refs": [f"{artifact_kind}.{str(action.get('operation') or 'update')}"],
        }

    def _pwa_asset_path(relative_path: str) -> Path:
        generated_asset = web_dir / "generated" / relative_path
        if generated_asset.exists():
            return generated_asset
        public_asset = pwa_public_dir / relative_path
        if public_asset.exists():
            return public_asset
        raise HTTPException(status_code=404, detail=f"PWA asset '{relative_path}' was not found.")

    def _surface_payloads_for_artifact_action(
        *,
        durable_scope: dict[str, Any],
        action: dict[str, Any],
    ) -> dict[str, Any]:
        context = action_surface_context(action)
        artifact_kind = str(action.get("artifact_kind") or "calendar")
        context_kind = str(context.get("kind") or ("task_focus" if artifact_kind == "task" else "calendar_day"))
        date_value = str(context.get("date") or "").strip() or str(
            (action.get("payload") if isinstance(action.get("payload"), dict) else {}).get("date") or "today"
        )
        if context_kind == "calendar_week":
            primary_surface = "calendar_week"
        elif context_kind == "task_focus" or artifact_kind == "task":
            primary_surface = "task_focus"
        else:
            primary_surface = "calendar_day"
        supporting_surfaces = ["task_focus"] if context_kind == "today_briefing" else []
        surface_invocation = {
            "intent": "task_focus" if primary_surface == "task_focus" else "schedule_lookup",
            "primary_surface": primary_surface,
            "supporting_surfaces": supporting_surfaces,
        }
        return _surface_payload_builder_for_scope(durable_scope).build_for_turn(
            message=f"{primary_surface} {date_value}",
            surface_invocation=surface_invocation,
        ).to_dict()

    @app.get("/api/health")
    def health(request: Request) -> dict[str, Any]:
        user_id = str(getattr(request.state, "user_id", "") or "")
        openai_key_status = _openai_key_status_for_request(request)
        model_auth_status = _model_auth_status_for_request(request)
        app_capabilities: dict[str, Any] | None = None
        if user_scoped_storage:
            workspace_id = None
            experiment = {"active": False, "session_id": None, "saved_note_count": 0}
            if user_id:
                durable_scope = _durable_scope(request)
                session = durable_scope["experiment_manager"].get_active_session()
                runtime = _runtime(durable_scope, session)
                workspace_id = runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
                experiment = _session_info(session)
                app_capabilities = _app_capability_manifest_for_scope(durable_scope)
        else:
            durable_scope = _durable_scope()
            session = durable_scope["experiment_manager"].get_active_session()
            runtime = _runtime(durable_scope, session)
            workspace_id = runtime["state_store"].get_active_workspace_id(default_workspace_id=cfg.active_workspace)
            experiment = _session_info(session)
            app_capabilities = _app_capability_manifest_for_scope(durable_scope)
        return {
            "status": "ok",
            "mode": model_auth_status["mode"],
            "model": cfg.model,
            "model_provider": model_auth_status["provider"],
            "model_auth": model_auth_status,
            "openai_key": openai_key_status,
            "workspace_id": workspace_id,
            "nexus_enabled": vault_store.is_enabled(),
            "experiment": experiment,
            "multi_user": multi_user_enabled,
            "auth_required": auth_enabled,
            "authenticated": bool(user_id) or not auth_enabled,
            "account_creation_enabled": account_creation_enabled,
            "account_creation_code_required": account_creation_code_required,
            "user": {"id": user_id} if user_id else None,
            "app_capabilities": app_capabilities,
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
                    "account_creation_code_required": False,
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
        if cfg.account_creation_code and not secrets.compare_digest(request.access_code or "", cfg.account_creation_code):
            raise HTTPException(status_code=403, detail="Invalid account access code.")
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
        user_root = _user_root_for_key(account_key)
        _ensure_storage_root(user_root)
        _seed_account_calendar_file(user_root)
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

    @app.get("/api/calendar/day")
    def get_calendar_day(request: Request, date: str | None = None) -> dict[str, Any]:
        try:
            target_date = resolve_calendar_date(date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _calendar_provider_for_scope(_durable_scope(request)).day(target_date).to_dict()

    @app.get("/api/calendar/week")
    def get_calendar_week(request: Request, date: str | None = None) -> dict[str, Any]:
        try:
            target_date = resolve_calendar_date(date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _calendar_provider_for_scope(_durable_scope(request)).week(target_date).to_dict()

    @app.get("/api/tasks/focus")
    def get_task_focus(request: Request, date: str | None = None) -> dict[str, Any]:
        try:
            target_date = resolve_calendar_date(date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _task_provider_for_scope(_durable_scope(request)).focus(target_date).to_dict()

    @app.post("/api/artifact-actions/{action_id}/accept")
    def accept_artifact_action(action_id: str, request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        store = _artifact_action_store_for_scope(durable_scope)
        try:
            action = store.load(action_id)
            accepted = execute_artifact_action(
                action=action,
                calendar_provider=_calendar_provider_for_scope(durable_scope),
                task_provider=_task_provider_for_scope(durable_scope),
            )
            store.update(accepted)
            surface_payload = _surface_payloads_for_artifact_action(durable_scope=durable_scope, action=accepted)
            return {
                "artifact_action": accepted,
                "artifact_actions": [accepted],
                "assistant_message": f"Done. {accepted.get('summary') or 'Artifact updated.'}",
                "graph_action": action_graph_payload(accepted),
                "surface_invocation": _artifact_action_surface_invocation_payload(accepted, existing=None),
                "app_capabilities": _app_capability_manifest_for_scope(durable_scope),
                **surface_payload,
            }
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            try:
                action = store.load(action_id)
                failed = store.update({**action, "status": "failed", "warnings": [str(exc)]})
                return {"artifact_action": failed, "artifact_actions": [failed], "assistant_message": str(exc)}
            except Exception:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/artifact-actions/{action_id}/reject")
    def reject_artifact_action_endpoint(action_id: str, request: Request) -> dict[str, Any]:
        durable_scope = _durable_scope(request)
        store = _artifact_action_store_for_scope(durable_scope)
        try:
            action = store.load(action_id)
            rejected = reject_artifact_action(action)
            store.update(rejected)
            return {
                "artifact_action": rejected,
                "artifact_actions": [rejected],
                "assistant_message": f"Okay, I left the {str(rejected.get('artifact_kind') or 'artifact')} unchanged.",
                "surface_invocation": _artifact_action_surface_invocation_payload(rejected, existing=None),
                "app_capabilities": _app_capability_manifest_for_scope(durable_scope),
            }
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/openai-key")
    def get_openai_key_status(request: Request) -> dict[str, Any]:
        scope_key = _scope_key_for_request(request)
        status = _openai_key_status(scope_key)
        model_auth_status = _model_auth_status(scope_key)
        return {
            "mode": model_auth_status["mode"],
            "model_provider": model_auth_status["provider"],
            "model_auth": model_auth_status,
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
        model_auth_status = _model_auth_status(scope_key)
        return {
            "mode": model_auth_status["mode"],
            "model_provider": model_auth_status["provider"],
            "model_auth": model_auth_status,
            "openai_key": status,
        }

    @app.delete("/api/openai-key")
    def delete_openai_key(request: Request) -> dict[str, Any]:
        scope_key = _scope_key_for_request(request)
        user_openai_api_keys.pop(scope_key, None)
        status = _openai_key_status(scope_key)
        model_auth_status = _model_auth_status(scope_key)
        return {
            "mode": model_auth_status["mode"],
            "model_provider": model_auth_status["provider"],
            "model_auth": model_auth_status,
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
                _serialize_concept_card(concept, scope=_record_scope(concept, durable_scope, session))
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
                _serialize_protocol_catalog_entry(entry, durable_scope, session)
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
            return _serialize_protocol_catalog_entry(entry, durable_scope, session)
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
            canonical_root=Path(durable_scope["canonical_scope"]["root"]),
            experiment_root=session.root if session is not None else None,
            runtime_scope="experiment" if session is not None else "durable",
        )
        return {"concepts": [candidate.to_dict() for candidate in candidates]}

    @app.get("/api/vault-notes/search")
    def search_vault_notes(query: str) -> dict[str, Any]:
        candidates = search_service.search(
            query=query,
            records=vault_store.list_notes(),
            limit=10,
            runtime_scope="reference",
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
            canonical_root=Path(durable_scope["canonical_scope"]["root"]),
            experiment_root=session.root if session is not None else None,
            runtime_scope="experiment" if session is not None else "durable",
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
                item = _serialize_saved_note_card(note, scope=_record_scope(note, durable_scope, session))
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
        return _serialize_concept_card(concept, scope=_record_scope(concept, durable_scope, session))

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
        if result.source_provenance is not None:
            payload["source_provenance"] = dict(result.source_provenance)
        if result.opened_copy is not None:
            payload["opened_copy"] = dict(result.opened_copy)
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
                visible_artifacts=request.visible_artifacts,
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

    @app.get("/manifest.webmanifest")
    def pwa_manifest() -> FileResponse:
        return FileResponse(
            _pwa_asset_path("manifest.webmanifest"),
            media_type="application/manifest+json",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/sw.js")
    def pwa_service_worker() -> FileResponse:
        return FileResponse(
            _pwa_asset_path("sw.js"),
            media_type="text/javascript",
            headers={
                "Cache-Control": "no-cache",
                "Service-Worker-Allowed": "/",
            },
        )

    @app.get("/icons/{filename}")
    def pwa_icon(filename: str) -> FileResponse:
        if filename not in PWA_ICON_FILES:
            raise HTTPException(status_code=404, detail="PWA icon was not found.")
        media_type = "image/svg+xml" if filename.endswith(".svg") else "image/png"
        return FileResponse(
            _pwa_asset_path(f"icons/{filename}"),
            media_type=media_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/")
    def index() -> FileResponse:
        react_index = web_dir / "generated" / "index.html"
        if react_index.exists():
            return FileResponse(react_index)
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


def _model_auth_openai_detail(openai_status: dict[str, Any]) -> str:
    source = str(openai_status.get("source") or "none")
    if source == "user":
        return "Using the OpenAI API key saved for this browser session."
    if source == "environment":
        return "Using the OpenAI API key from the Vantage environment."
    return "No model credential is configured."


def _resolve_repo_path(repo_root: Path, path: Path | None, *, default_relative: str) -> Path:
    candidate = path or Path(default_relative)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


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
