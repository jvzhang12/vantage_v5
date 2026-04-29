from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import json
from pathlib import Path
import re
from typing import Any

from openai import OpenAI

from vantage_v5.services.draft_artifact_lifecycle import artifact_lifecycle_card_fields
from vantage_v5.services.draft_artifact_lifecycle import artifact_lifecycle_kind
from vantage_v5.services.executor import ExecutedAction
from vantage_v5.services.executor import GraphActionExecutor
from vantage_v5.services.meta import MetaDecision
from vantage_v5.services.meta import MetaService
from vantage_v5.services.protocol_engine import ProtocolEngine
from vantage_v5.services.response_mode import build_response_mode_payload
from vantage_v5.services.response_mode import finalize_assistant_message
from vantage_v5.services.search import CandidateMemory
from vantage_v5.services.search import ConceptSearchService
from vantage_v5.services.turn_payloads import assemble_chat_turn_body
from vantage_v5.services.turn_payloads import ChatTurnBodyParts
from vantage_v5.services.turn_staging import audit_stage_response
from vantage_v5.services.turn_staging import initial_stage_progress
from vantage_v5.services.turn_staging import stage_progress_event
from vantage_v5.services.turn_staging import StageAuditResult
from vantage_v5.services.turn_staging import TurnStage
from vantage_v5.services.vetting import anchor_selected_record_candidate
from vantage_v5.services.vetting import build_continuity_hint
from vantage_v5.services.vetting import resolve_selected_record_candidate
from vantage_v5.services.vetting import should_preserve_selected_record
from vantage_v5.services.vetting import ConceptVettingService
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.memory_trace import parse_memory_trace_metadata
from vantage_v5.storage.memory_trace import MemoryTraceStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.vault import VaultNoteStore
from vantage_v5.storage.workspaces import WorkspaceDocument
from vantage_v5.storage.workspaces import WorkspaceStore

WHITEBOARD_LABEL_RE = re.compile(
    r"(?<![A-Z0-9_])(?P<label>CHAT_RESPONSE|WHITEBOARD_DRAFT|WHITEBOARD_OFFER)\s*:",
    re.IGNORECASE,
)

logger = logging.getLogger(__name__)


class ModelReplyError(RuntimeError):
    pass


@dataclass(slots=True)
class WorkspaceDraft:
    content: str
    summary: str


@dataclass(slots=True)
class WorkspaceOffer:
    summary: str


@dataclass(frozen=True, slots=True)
class ReplyVerification:
    ok: bool
    repair_strategy: str = "accept"
    issues: tuple[str, ...] = ()
    retry_instruction: str = ""


@dataclass(slots=True)
class ChatTurn:
    user_message: str
    assistant_message: str
    workspace_id: str
    workspace_title: str
    concept_cards: list[dict]
    trace_notes: list[dict]
    saved_notes: list[dict]
    vault_notes: list[dict]
    candidate_concepts: list[dict]
    candidate_trace_notes: list[dict]
    candidate_saved_notes: list[dict]
    candidate_vault_notes: list[dict]
    candidate_memory: list[dict]
    working_memory: list[dict]
    recall_details: list[dict]
    learned: list[dict]
    response_mode: dict
    vetting: dict
    mode: str
    workspace_content: str | None = None
    workspace_update: dict | None = None
    memory_trace_record: dict | None = None
    meta_action: dict | None = None
    graph_action: dict | None = None
    created_record: dict | None = None
    turn_stage: dict | None = None
    stage_progress: list[dict] | None = None
    stage_audit: dict | None = None

    def to_body_parts(self) -> ChatTurnBodyParts:
        return ChatTurnBodyParts(
            user_message=self.user_message,
            assistant_message=self.assistant_message,
            workspace_id=self.workspace_id,
            workspace_title=self.workspace_title,
            workspace_content=self.workspace_content,
            workspace_update=self.workspace_update,
            concept_cards=self.concept_cards,
            trace_notes=self.trace_notes,
            saved_notes=self.saved_notes,
            vault_notes=self.vault_notes,
            candidate_concepts=self.candidate_concepts,
            candidate_trace_notes=self.candidate_trace_notes,
            candidate_saved_notes=self.candidate_saved_notes,
            candidate_vault_notes=self.candidate_vault_notes,
            candidate_memory=self.candidate_memory,
            working_memory=self.working_memory,
            recall_details=self.recall_details,
            learned=self.learned,
            memory_trace_record=self.memory_trace_record,
            response_mode=self.response_mode,
            vetting=self.vetting,
            mode=self.mode,
            meta_action=self.meta_action,
            graph_action=self.graph_action,
            created_record=self.created_record,
            turn_stage=self.turn_stage,
            stage_progress=self.stage_progress,
            stage_audit=self.stage_audit,
        )

    def to_dict(self) -> dict:
        return assemble_chat_turn_body(self.to_body_parts())


class ChatService:
    def __init__(
        self,
        *,
        model: str,
        openai_api_key: str | None,
        concept_store: ConceptStore,
        reference_concept_store: ConceptStore | None,
        memory_store: MemoryStore,
        memory_trace_store: MemoryTraceStore,
        artifact_store: ArtifactStore,
        workspace_store: WorkspaceStore,
        reference_memory_store: MemoryStore | None,
        reference_memory_trace_store: MemoryTraceStore | None,
        reference_artifact_store: ArtifactStore | None,
        vault_store: VaultNoteStore,
        search_service: ConceptSearchService,
        vetting_service: ConceptVettingService,
        meta_service: MetaService,
        protocol_engine: ProtocolEngine,
        executor: GraphActionExecutor,
        traces_dir: Path,
    ) -> None:
        self.model = model
        self.concept_store = concept_store
        self.reference_concept_store = reference_concept_store
        self.memory_store = memory_store
        self.memory_trace_store = memory_trace_store
        self.artifact_store = artifact_store
        self.workspace_store = workspace_store
        self.reference_memory_store = reference_memory_store
        self.reference_memory_trace_store = reference_memory_trace_store
        self.reference_artifact_store = reference_artifact_store
        self.vault_store = vault_store
        self.search_service = search_service
        self.vetting_service = vetting_service
        self.meta_service = meta_service
        self.protocol_engine = protocol_engine
        self.executor = executor
        self.traces_dir = traces_dir
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None

    def reply(
        self,
        *,
        message: str,
        workspace: WorkspaceDocument,
        history: list[dict[str, str]],
        memory_intent: str = "auto",
        selected_record_id: str | None = None,
        whiteboard_mode: str = "auto",
        preserve_selected_record: bool | None = None,
        selected_record_reason: str | None = None,
        pending_workspace_update: dict[str, Any] | None = None,
        workspace_is_transient: bool = False,
        workspace_scope: str = "excluded",
        applied_protocol_kinds: list[str] | None = None,
        turn_stage: TurnStage | None = None,
    ) -> ChatTurn:
        memory_mode = _normalize_memory_mode(memory_intent)
        whiteboard_mode = _normalize_whiteboard_mode(whiteboard_mode)
        concepts = _merge_records(
            self.concept_store.list_concepts(),
            self.reference_concept_store.list_concepts() if self.reference_concept_store else [],
        )
        protocol_turn = self.protocol_engine.interpret_and_apply(
            message=message,
            history=history,
            concept_records=concepts,
            concept_store=self.concept_store,
        )
        concepts = list(protocol_turn.concept_records)
        protocol_action = protocol_turn.protocol_action
        memory_traces = _merge_records(
            self.memory_trace_store.list_recent_traces(),
            self.reference_memory_trace_store.list_recent_traces() if self.reference_memory_trace_store else [],
        )
        saved_notes = _merge_saved_records(
            self.memory_store.list_memories(),
            self.artifact_store.list_artifacts(),
            self.reference_memory_store.list_memories() if self.reference_memory_store else [],
            self.reference_artifact_store.list_artifacts() if self.reference_artifact_store else [],
        )
        vault_notes = self.vault_store.list_notes()
        selected_memory = resolve_selected_record_candidate(
            selected_record_id,
            self.concept_store,
            self.reference_concept_store,
            self.memory_store,
            self.reference_memory_store,
            self.artifact_store,
            self.reference_artifact_store,
            self.vault_store,
            reason=selected_record_reason,
        )
        preserve_selected_memory = preserve_selected_record
        if preserve_selected_memory is None:
            preserve_selected_memory = should_preserve_selected_record(
                message=message,
                history=history,
                selected_memory=selected_memory,
                pending_workspace_update=pending_workspace_update,
                workspace=workspace,
                workspace_scope=workspace_scope,
            )
        continuity_hint = build_continuity_hint(
            message=message,
            history=history,
            selected_memory=selected_memory,
            preserve_selected_record=preserve_selected_memory,
            selected_record_reason=selected_record_reason,
            pending_workspace_update=pending_workspace_update,
            workspace=workspace,
            workspace_scope=workspace_scope,
        )
        if preserve_selected_memory and selected_memory is not None:
            selected_memory.why_recalled = (
                selected_record_reason
                or (continuity_hint.summary if continuity_hint else None)
                or f"Selected record '{selected_memory.title}' is in focus for this turn."
            )
        candidate_memory = self.search_service.search_context(
            query=message,
            memory_trace_records=memory_traces,
            concept_records=concepts,
            saved_note_records=saved_notes,
            vault_records=vault_notes,
            workspace_id=workspace.workspace_id,
            workspace_title=workspace.title,
            workspace_scope=workspace_scope,
            selected_record_id=selected_memory.id if preserve_selected_memory and selected_memory else None,
            selected_record_source=selected_memory.source if preserve_selected_memory and selected_memory else None,
            limit=16,
        )
        protocol_guidance = self.protocol_engine.build_guidance(
            protocol_kinds=[
                *(applied_protocol_kinds or []),
                *protocol_turn.recall_protocol_kinds,
            ],
            concept_records=concepts,
        )
        protocol_candidates = protocol_guidance.candidate_memory()
        if protocol_candidates:
            candidate_memory = _merge_candidate_memory(protocol_candidates, candidate_memory, limit=16)
        if preserve_selected_memory and selected_memory is not None:
            candidate_memory = _merge_candidate_memory([selected_memory], candidate_memory, limit=16)
        vetted_memory, vetting = self.vetting_service.vet(
            message=message,
            candidates=candidate_memory,
            continuity_hint=continuity_hint.to_dict() if continuity_hint else None,
        )
        if preserve_selected_memory and selected_memory is not None:
            vetted_memory, vetting = anchor_selected_record_candidate(
                vetted_memory,
                vetting,
                selected_memory,
                continuity_reason=selected_record_reason,
            )
        vetted_concepts = [item for item in vetted_memory if item.source == "concept"]
        vetted_trace_notes = [item for item in vetted_memory if item.source == "memory_trace"]
        vetted_saved_notes = [item for item in vetted_memory if item.source in {"memory", "artifact"}]
        vetted_vault_notes = [item for item in vetted_memory if item.source == "vault_note"]
        candidate_concepts = [item for item in candidate_memory if item.source == "concept"]
        candidate_trace_notes = [item for item in candidate_memory if item.source == "memory_trace"]
        candidate_saved_notes = [item for item in candidate_memory if item.source in {"memory", "artifact"}]
        candidate_vault_notes = [item for item in candidate_memory if item.source == "vault_note"]
        stage_progress = initial_stage_progress(turn_stage) if turn_stage is not None else []
        stage_audit: StageAuditResult | None = None
        if self.client:
            try:
                (
                    assistant_message,
                    workspace_draft,
                    workspace_offer,
                    model_stage_progress,
                    stage_audit,
                ) = self._openai_reply_with_stage(
                    message=message,
                    workspace=workspace,
                    history=history,
                    vetted_memory=vetted_memory,
                    selected_memory=selected_memory if preserve_selected_memory else None,
                    whiteboard_mode=whiteboard_mode,
                    pending_workspace_update=pending_workspace_update,
                    turn_stage=turn_stage,
                )
                stage_progress.extend(model_stage_progress)
            except ModelReplyError:
                logger.exception("OpenAI chat reply failed; falling back to deterministic chat response.")
                assistant_message, workspace_draft, workspace_offer = self._fallback_reply(
                    message=message,
                    workspace=workspace,
                    vetted_memory=vetted_memory,
                    whiteboard_mode=whiteboard_mode,
                    pending_workspace_update=pending_workspace_update,
                    fallback_reason="provider_error",
                )
                stage_progress.append(
                    stage_progress_event(
                        "stage_generate",
                        "Generated fallback response",
                        message="The model provider was unavailable, so Vantage used the safe fallback path.",
                    )
                )
                stage_audit = audit_stage_response(
                    stage=turn_stage,
                    assistant_message=assistant_message,
                    has_workspace_draft=workspace_draft is not None,
                    has_workspace_offer=workspace_offer is not None,
                    attempt=1,
                )
                stage_progress.append(
                    stage_progress_event(
                        "stage_audit",
                        "Checked output",
                        status="completed" if stage_audit.accepted else "failed",
                        message=_stage_audit_progress_message(stage_audit),
                    )
                )
                mode = "fallback"
            else:
                mode = "openai"
        else:
            assistant_message, workspace_draft, workspace_offer = self._fallback_reply(
                message=message,
                workspace=workspace,
                vetted_memory=vetted_memory,
                whiteboard_mode=whiteboard_mode,
                pending_workspace_update=pending_workspace_update,
            )
            stage_progress.append(
                stage_progress_event(
                    "stage_generate",
                    "Generated fallback response",
                    message="The local fallback path kept the turn responsive.",
                )
            )
            stage_audit = audit_stage_response(
                stage=turn_stage,
                assistant_message=assistant_message,
                has_workspace_draft=workspace_draft is not None,
                has_workspace_offer=workspace_offer is not None,
                attempt=1,
            )
            stage_progress.append(
                stage_progress_event(
                    "stage_audit",
                    "Checked output",
                    status="completed" if stage_audit.accepted else "failed",
                    message=_stage_audit_progress_message(stage_audit),
                )
            )
            mode = "fallback"
        response_mode = build_response_mode_payload(
            vetted_memory,
            workspace_has_context=bool(workspace.content.strip()),
            history_has_context=bool(history),
            pending_workspace_has_context=bool(pending_workspace_update),
        )
        recall_details = [candidate.to_recall_dict() for candidate in vetted_memory]
        assistant_message = finalize_assistant_message(
            assistant_message,
            response_mode=response_mode,
            suppress_best_guess_preface=whiteboard_mode in {"offer", "draft"},
        )
        workspace_update = None
        auto_artifact_action = None
        auto_artifact_record = None
        if workspace_draft is not None:
            workspace_draft = _enforce_workspace_draft_constraints(
                message=message,
                draft=workspace_draft,
                workspace=workspace,
                vetted_memory=vetted_memory,
            )
            draft_workspace = WorkspaceDocument(
                workspace_id=workspace.workspace_id,
                title=_workspace_title_from_content(workspace.workspace_id, workspace_draft.content),
                content=workspace_draft.content,
                path=workspace.path,
                scenario_metadata=WorkspaceStore.parse_scenario_metadata(
                    workspace_draft.content,
                    workspace_id=workspace.workspace_id,
                ),
            )
            auto_artifact_action = self.executor.save_workspace_iteration_artifact(
                workspace=draft_workspace,
                title=draft_workspace.title,
                card=workspace_draft.summary,
                body=workspace_draft.content,
            )
            auto_artifact_record = self._created_record_payload(auto_artifact_action)
            workspace_update = {
                "type": "draft_whiteboard",
                "status": "draft_ready",
                "decision": None,
                "proposal_kind": "draft",
                "summary": workspace_draft.summary,
                "workspace_id": workspace.workspace_id,
                "title": draft_workspace.title,
                "content": workspace_draft.content,
                "persisted": False,
                "artifact_snapshot_id": auto_artifact_record["id"] if auto_artifact_record else None,
            }
        elif workspace_offer is not None:
            workspace_update = {
                "type": "offer_whiteboard",
                "status": "offered",
                "decision": None,
                "proposal_kind": "offer",
                "summary": workspace_offer.summary,
                "workspace_id": workspace.workspace_id,
                "title": workspace.title,
                "content": None,
                "persisted": False,
            }
        if protocol_action is not None:
            meta = MetaDecision(
                action="no_op",
                rationale=(
                    "A reusable protocol was updated deterministically, so no separate meta write was needed."
                ),
            )
            executed_action = None
        else:
            meta = self.meta_service.decide(
                user_message=message,
                assistant_message=assistant_message,
                workspace=workspace,
                vetted_items=vetted_memory,
                history=history,
                memory_mode=memory_mode,
                workspace_update=workspace_update,
            )
            executed_action = self.executor.execute(meta, workspace=workspace)
        created_record = self._created_record_payload(executed_action)
        protocol_record_payload = self._created_record_payload(protocol_action)
        learned_records = [
            record
            for record in [protocol_record_payload, created_record, auto_artifact_record]
            if record is not None
        ]
        memory_trace_record = self.memory_trace_store.create_turn_trace(
            user_message=message,
            assistant_message=assistant_message,
            working_memory=[candidate.to_dict() for candidate in vetted_memory],
            history=history,
            workspace_id=workspace.workspace_id,
            workspace_title=workspace.title,
            workspace_content=None if workspace_is_transient else workspace.content,
            workspace_scope=workspace_scope,
            learned=learned_records,
            response_mode=response_mode,
            scope="experiment" if "experiments" in self.memory_trace_store.records_dir.parts else "durable",
            pending_workspace_update=pending_workspace_update,
            turn_mode="chat",
            preserved_context=_trace_preserved_context_payload(selected_memory if preserve_selected_memory else None),
            referenced_record=_trace_referenced_record_payload(
                vetted_memory=vetted_memory,
                selected_memory=selected_memory if preserve_selected_memory else None,
            ),
        )

        turn = ChatTurn(
            user_message=message,
            assistant_message=assistant_message,
            workspace_id=workspace.workspace_id,
            workspace_title=workspace.title,
            workspace_content=workspace.content if workspace_is_transient else None,
            workspace_update=workspace_update,
            concept_cards=[candidate.to_dict() for candidate in vetted_concepts],
            trace_notes=[candidate.to_dict() for candidate in vetted_trace_notes],
            saved_notes=[candidate.to_dict() for candidate in vetted_saved_notes],
            vault_notes=[candidate.to_dict() for candidate in vetted_vault_notes],
            candidate_concepts=[candidate.to_dict() for candidate in candidate_concepts],
            candidate_trace_notes=[candidate.to_dict() for candidate in candidate_trace_notes],
            candidate_saved_notes=[candidate.to_dict() for candidate in candidate_saved_notes],
            candidate_vault_notes=[candidate.to_dict() for candidate in candidate_vault_notes],
            candidate_memory=[candidate.to_dict() for candidate in candidate_memory],
            working_memory=recall_details,
            recall_details=recall_details,
            learned=learned_records,
            memory_trace_record=self._memory_trace_payload(memory_trace_record),
            response_mode=response_mode,
            vetting=vetting,
            mode=mode,
            meta_action=meta.to_dict(),
            graph_action=_graph_action_payload(executed_action, meta)
            or _auto_graph_action_payload(auto_artifact_action)
            or _auto_graph_action_payload(protocol_action),
            created_record=created_record or auto_artifact_record or protocol_record_payload,
            turn_stage=turn_stage.to_dict() if turn_stage is not None else None,
            stage_progress=stage_progress,
            stage_audit=stage_audit.to_dict() if stage_audit is not None else None,
        )
        self._trace_turn(
            turn,
            workspace,
            history,
            memory_mode=memory_mode,
            whiteboard_mode=whiteboard_mode,
            selected_record_id=selected_record_id,
            preserve_selected_record=preserve_selected_memory,
            selected_record_reason=selected_record_reason,
            pending_workspace_update=pending_workspace_update,
            workspace_is_transient=workspace_is_transient,
            workspace_scope=workspace_scope,
        )
        return turn

    def _openai_reply_with_stage(
        self,
        *,
        message: str,
        workspace: WorkspaceDocument,
        history: list[dict[str, str]],
        vetted_memory: list[CandidateMemory],
        selected_memory: CandidateMemory | None,
        whiteboard_mode: str,
        pending_workspace_update: dict[str, Any] | None,
        turn_stage: TurnStage | None,
    ) -> tuple[str, WorkspaceDraft | None, WorkspaceOffer | None, list[dict[str, Any]], StageAuditResult]:
        max_attempts = turn_stage.max_attempts if turn_stage is not None else 1
        retry_instruction = ""
        stage_progress: list[dict[str, Any]] = []
        last_reply: tuple[str, WorkspaceDraft | None, WorkspaceOffer | None] | None = None
        last_audit = StageAuditResult(accepted=True, status="accepted")
        for attempt in range(1, max_attempts + 1):
            try:
                assistant_reply = self._openai_reply(
                    message=message,
                    workspace=workspace,
                    history=history,
                    vetted_memory=vetted_memory,
                    selected_memory=selected_memory,
                    whiteboard_mode=whiteboard_mode,
                    pending_workspace_update=pending_workspace_update,
                    turn_stage=turn_stage,
                    stage_retry_instruction=retry_instruction or None,
                )
            except Exception as exc:
                raise ModelReplyError("Model-backed chat generation failed.") from exc
            assistant_message, workspace_draft, workspace_offer = self._normalize_openai_reply(
                response_text=assistant_reply,
                message=message,
                whiteboard_mode=whiteboard_mode,
                pending_workspace_update=pending_workspace_update,
            )
            last_reply = (assistant_message, workspace_draft, workspace_offer)
            stage_progress.append(
                stage_progress_event(
                    "stage_generate",
                    "Generated response" if attempt == 1 else "Regenerated response",
                    message="Vantage drafted the response against the staged turn contract.",
                    attempt=attempt,
                )
            )
            last_audit = audit_stage_response(
                stage=turn_stage,
                assistant_message=assistant_message,
                has_workspace_draft=workspace_draft is not None,
                has_workspace_offer=workspace_offer is not None,
                attempt=attempt,
            )
            stage_progress.append(
                stage_progress_event(
                    "stage_audit",
                    "Checked output",
                    status="completed" if last_audit.accepted else ("retrying" if last_audit.retryable else "failed"),
                    message=_stage_audit_progress_message(last_audit),
                    attempt=attempt,
                )
            )
            if last_audit.accepted:
                stage_progress.append(
                    stage_progress_event(
                        "stage_accept",
                        "Accepted response",
                        message="The response matched the requested surface.",
                        attempt=attempt,
                    )
                )
                return assistant_message, workspace_draft, workspace_offer, stage_progress, last_audit
            if not last_audit.retryable:
                break
            retry_instruction = last_audit.retry_instruction
            stage_progress.append(
                stage_progress_event(
                    "stage_restage",
                    "Restaged context",
                    status="retrying",
                    message="The first response missed the requested surface, so Vantage regenerated it before saving anything.",
                    attempt=attempt + 1,
                )
            )
        if last_reply is None:
            return "", None, None, stage_progress, last_audit
        assistant_message, workspace_draft, workspace_offer = last_reply
        if last_audit.status == "terminal" and "internal_or_provider_text" in last_audit.issues:
            return (
                "I could not safely return that response. Please try again in a moment.",
                None,
                None,
                stage_progress,
                last_audit,
            )
        return assistant_message, workspace_draft, workspace_offer, stage_progress, last_audit

    def _openai_reply(
        self,
        *,
        message: str,
        workspace: WorkspaceDocument,
        history: list[dict[str, str]],
        vetted_memory: list[CandidateMemory],
        selected_memory: CandidateMemory | None,
        whiteboard_mode: str,
        pending_workspace_update: dict[str, Any] | None,
        turn_stage: TurnStage | None = None,
        stage_retry_instruction: str | None = None,
    ) -> str:
        recent_history = history[-6:]
        selected_memory_payload = None
        if selected_memory is not None:
            selected_memory_payload = {
                "id": selected_memory.id,
                "title": selected_memory.title,
                "card": selected_memory.card,
                "body": (selected_memory.body or "")[:1200],
                "source": selected_memory.source,
            }
            if selected_memory.path:
                selected_memory_payload["path"] = selected_memory.path
        input_payload = {
            "recent_chat": recent_history,
            "workspace_title": workspace.title,
            "workspace_content": workspace.content,
            "relevant_memory": [item.to_dict() for item in vetted_memory],
            "selected_memory": selected_memory_payload,
            "pending_workspace_update": pending_workspace_update,
            "user_message": message,
            "whiteboard_mode": whiteboard_mode,
            "turn_stage": turn_stage.to_dict() if turn_stage is not None else None,
            "stage_retry_instruction": stage_retry_instruction,
        }
        instructions = (
            "You are Vantage V5. "
            "Behave like a normal high-quality chat assistant. "
            "When relevant, use the shared Markdown workspace as collaborative context. "
            "Use the vetted memory items as bounded context when they are relevant. "
            "Treat Memory Trace items as recent continuity history, not timeless knowledge. "
            "Treat Vantage concepts as timeless reasoning knowledge. "
            "Treat Vantage protocols as modifiable instructions for recurring work types; "
            "when relevant_memory includes an item with type protocol, follow its variables and procedure unless the current user message overrides it. "
            "Treat saved memories and artifacts as continuity and work-history context. "
            "Treat Nexus vault notes as read-only reference material rather than guaranteed truth. "
            "You may reference and improve the workspace, but do not claim to have saved memory or modified files unless explicitly told so by the system. "
            "The request payload includes whiteboard_mode, which can be auto, offer, draft, or chat. "
            "If whiteboard_mode is chat, do not use any WHITEBOARD_* special format. "
            "If whiteboard_mode is offer and the user is asking for a concrete work product, prefer the WHITEBOARD_OFFER format. "
            "If whiteboard_mode is draft and the user is asking for a concrete work product, prefer the WHITEBOARD_DRAFT format. "
            "The payload may include pending_workspace_update from the previous turn, including the origin request for a still-open whiteboard invitation or draft. "
            "When pending_workspace_update is present, treat it as live drafting context. "
            "If the current user message is a short acceptance, confirmation, preference-setting confirmation, refinement, or continuation of that pending whiteboard flow, use the original work-product request from pending_workspace_update to produce the actual draft now. "
            "Do not repeat the whiteboard invitation after the user has already accepted a pending offer. "
            "When the user is asking for a concrete work product such as an email, plan, itinerary, list, essay, paper, code, outline, checklist, agenda, or other document, first invite whiteboard collaboration unless one of three things is already true: "
            "the user explicitly asked to use the whiteboard, the user is clearly continuing an existing whiteboard draft, or the user explicitly asked for the full output directly in chat. "
            "For that invitation, respond exactly in this two-line format:\n"
            "CHAT_RESPONSE: <one or two sentences asking whether the user wants to pull up a whiteboard for this work product>\n"
            "WHITEBOARD_OFFER: <one sentence describing what could be drafted in the whiteboard>.\n"
            "When the user has already chosen the whiteboard or clearly wants collaborative drafting there, respond exactly in this two-line format:\n"
            "CHAT_RESPONSE: <one to three sentences telling the user the detailed draft is now in the whiteboard>\n"
            "WHITEBOARD_DRAFT: <complete Markdown draft beginning with a level-one heading>.\n"
            "The whiteboard draft should contain the full structured content and should be ready for collaborative editing. "
            "Use these special formats only for concrete work products and whiteboard collaboration. "
            "Otherwise, respond normally with just the assistant message."
        )
        if stage_retry_instruction:
            instructions += (
                " A prior response failed the staged turn contract before anything was saved. "
                "Regenerate the response and follow stage_retry_instruction from the payload exactly."
            )
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=instructions,
            input=json.dumps(input_payload),
        )
        return response.output_text.strip()

    def _normalize_openai_reply(
        self,
        *,
        response_text: str,
        message: str,
        whiteboard_mode: str,
        pending_workspace_update: dict[str, Any] | None,
    ) -> tuple[str, WorkspaceDraft | None, WorkspaceOffer | None]:
        assistant_message, workspace_draft, workspace_offer = _extract_workspace_signal(
            response_text,
            whiteboard_mode=whiteboard_mode,
        )
        if workspace_draft is not None or workspace_offer is not None or whiteboard_mode == "chat":
            return assistant_message, workspace_draft, workspace_offer
        if whiteboard_mode not in {"offer", "draft"}:
            return assistant_message, workspace_draft, workspace_offer
        try:
            verification = self._verify_openai_reply(
                response_text=response_text,
                message=message,
                whiteboard_mode=whiteboard_mode,
                pending_workspace_update=pending_workspace_update,
                parsed_assistant_message=assistant_message,
                workspace_draft=workspace_draft,
                workspace_offer=workspace_offer,
            )
        except Exception:
            logger.exception("OpenAI reply verification failed; using unverified response text.")
            verification = ReplyVerification(
                ok=True,
                repair_strategy="accept",
                issues=("verifier_unavailable",),
                retry_instruction="",
            )
        if verification.ok or verification.repair_strategy == "accept":
            return assistant_message, workspace_draft, workspace_offer
        if verification.repair_strategy == "fallback_safe_message":
            return (
                "I could not safely turn that into the requested whiteboard action. Please try again in a moment.",
                None,
                None,
            )
        try:
            return self._structure_openai_reply(
                response_text=response_text,
                message=message,
                whiteboard_mode=whiteboard_mode,
                pending_workspace_update=pending_workspace_update,
                verifier_feedback=verification,
            )
        except Exception:
            logger.exception("OpenAI reply structuring failed; using unstructured assistant text.")
            return assistant_message, workspace_draft, workspace_offer

    def _verify_openai_reply(
        self,
        *,
        response_text: str,
        message: str,
        whiteboard_mode: str,
        pending_workspace_update: dict[str, Any] | None,
        parsed_assistant_message: str,
        workspace_draft: WorkspaceDraft | None,
        workspace_offer: WorkspaceOffer | None,
    ) -> ReplyVerification:
        del workspace_draft, workspace_offer
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are the Vantage response verifier. "
                "Judge whether the assistant response satisfies the requested product contract. "
                "Do not rewrite the answer. Choose a bounded repair strategy only. "
                "Use accept when the response can be returned as-is. "
                "Use normalize_json when the response should be converted into typed whiteboard action fields. "
                "Use retry_response only when the response substantially conflicts with the requested surface or constraints. "
                "Use fallback_safe_message only when the response contains unsafe/internal/provider/debug content. "
                "For whiteboard_mode draft, a satisfactory response must provide or imply a complete draft for the whiteboard, not merely offer one. "
                "For whiteboard_mode offer, a satisfactory response should be an invitation/offer rather than a full draft. "
                "Return only JSON matching the schema."
            ),
            input=json.dumps(
                {
                    "user_message": message,
                    "assistant_response": response_text,
                    "parsed_assistant_message": parsed_assistant_message,
                    "whiteboard_mode": whiteboard_mode,
                    "pending_workspace_update": pending_workspace_update,
                }
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "vantage_response_verification",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "ok": {"type": "boolean"},
                            "repair_strategy": {
                                "type": "string",
                                "enum": ["accept", "normalize_json", "retry_response", "fallback_safe_message"],
                            },
                            "issues": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "retry_instruction": {"type": ["string", "null"]},
                        },
                        "required": ["ok", "repair_strategy", "issues", "retry_instruction"],
                    },
                }
            },
        )
        payload = json.loads(response.output_text)
        strategy = str(payload.get("repair_strategy") or "accept").strip().lower()
        if strategy not in {"accept", "normalize_json", "retry_response", "fallback_safe_message"}:
            strategy = "accept"
        raw_issues = payload.get("issues") if isinstance(payload.get("issues"), list) else []
        issues = tuple(str(issue).strip() for issue in raw_issues if str(issue).strip())
        return ReplyVerification(
            ok=bool(payload.get("ok")) and strategy == "accept",
            repair_strategy=strategy,
            issues=issues,
            retry_instruction=str(payload.get("retry_instruction") or "").strip(),
        )

    def _structure_openai_reply(
        self,
        *,
        response_text: str,
        message: str,
        whiteboard_mode: str,
        pending_workspace_update: dict[str, Any] | None,
        verifier_feedback: ReplyVerification | None = None,
    ) -> tuple[str, WorkspaceDraft | None, WorkspaceOffer | None]:
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are the Vantage response normalizer. "
                "Convert the assistant's natural-language reply into a strict product contract. "
                "Do not invent new content beyond extracting or lightly restating what is present. "
                "If whiteboard_mode is offer, prefer action offer unless the reply clearly should stay as plain chat. "
                "If whiteboard_mode is draft, prefer action draft when the reply contains or implies a complete work product draft. "
                "Protocols are guidance, not draft targets; never set a protocol document as draft_markdown. "
                "If verifier_feedback is present, use its issues and retry_instruction to repair the contract while staying grounded in the original assistant response and user request. "
                "Return only JSON matching the schema."
            ),
            input=json.dumps(
                {
                    "user_message": message,
                    "assistant_response": response_text,
                    "whiteboard_mode": whiteboard_mode,
                    "pending_workspace_update": pending_workspace_update,
                    "verifier_feedback": _verification_payload(verifier_feedback),
                }
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "vantage_response_contract",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "assistant_message": {"type": "string"},
                            "whiteboard_action": {
                                "type": "string",
                                "enum": ["none", "offer", "draft"],
                            },
                            "offer_summary": {"type": ["string", "null"]},
                            "draft_markdown": {"type": ["string", "null"]},
                        },
                        "required": [
                            "assistant_message",
                            "whiteboard_action",
                            "offer_summary",
                            "draft_markdown",
                        ],
                    },
                }
            },
        )
        payload = json.loads(response.output_text)
        assistant_message = str(payload.get("assistant_message") or "").strip() or response_text.strip()
        action = str(payload.get("whiteboard_action") or "none").strip().lower()
        if whiteboard_mode == "offer" and action == "draft":
            action = "offer"
        if action == "offer" and whiteboard_mode != "chat":
            offer_summary = " ".join(str(payload.get("offer_summary") or "").strip().split())
            if not offer_summary:
                offer_summary = "Whiteboard available for collaborative drafting."
            return assistant_message, None, WorkspaceOffer(summary=offer_summary)
        if action == "draft" and whiteboard_mode == "draft":
            draft_content = _normalize_workspace_draft_content(str(payload.get("draft_markdown") or ""))
            if draft_content:
                return assistant_message, WorkspaceDraft(
                    content=draft_content,
                    summary="Drafted the detailed answer into the whiteboard for collaborative editing.",
                ), None
        return assistant_message, None, None

    @staticmethod
    def _fallback_reply(
        *,
        message: str,
        workspace: WorkspaceDocument,
        vetted_memory: list[CandidateMemory],
        whiteboard_mode: str = "auto",
        pending_workspace_update: dict[str, Any] | None = None,
        fallback_reason: str = "no_openai_key",
    ) -> tuple[str, WorkspaceDraft | None, WorkspaceOffer | None]:
        if whiteboard_mode == "offer":
            return (
                "Want me to open the whiteboard so we can draft this there?",
                None,
                WorkspaceOffer(summary=_fallback_offer_summary(message)),
            )
        if whiteboard_mode == "draft":
            draft_request = _fallback_draft_request(
                message=message,
                pending_workspace_update=pending_workspace_update,
            )
            if _can_make_fallback_draft(
                message=message,
                workspace=workspace,
                pending_workspace_update=pending_workspace_update,
            ):
                draft_content = _fallback_workspace_draft(draft_request)
                return (
                    "I put a simple draft in the whiteboard so you can keep moving. It may need another pass once the model is available.",
                    WorkspaceDraft(
                        content=draft_content,
                        summary="Fallback draft prepared in the whiteboard while the model was unavailable.",
                    ),
                    None,
                )
            return (
                "I could not safely update the whiteboard on this turn, so I left the current draft unchanged. Please try again in a moment.",
                None,
                None,
            )
        if fallback_reason == "provider_error":
            return (
                "I could not complete the model-backed answer on this turn. Please try again in a moment.",
                None,
                None,
            )
        context_hint = "I can still keep the app responsive, but model-backed answers are not configured here."
        if vetted_memory:
            context_hint += " I found some local context, but I cannot turn it into a complete answer without the model-backed response."
        return context_hint, None, None

    def _trace_turn(
        self,
        turn: ChatTurn,
        workspace: WorkspaceDocument,
        history: list[dict[str, str]],
        *,
        memory_mode: str,
        whiteboard_mode: str,
        selected_record_id: str | None,
        preserve_selected_record: bool | None,
        selected_record_reason: str | None,
        pending_workspace_update: dict[str, Any] | None = None,
        workspace_is_transient: bool = False,
        workspace_scope: str = "excluded",
    ) -> None:
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        trace_path = self._next_trace_path()
        turn_payload = turn.to_dict()
        if workspace_is_transient:
            workspace_payload = dict(turn_payload.get("workspace") or {})
            workspace_payload["content"] = None
            turn_payload["workspace"] = workspace_payload
        trace_path.write_text(
            json.dumps(
                {
                    "turn": turn_payload,
                    "workspace_excerpt": None if workspace_is_transient else workspace.content[:1200],
                    "workspace_is_transient": workspace_is_transient,
                    "history": history[-6:],
                    "memory_mode": memory_mode,
                    "whiteboard_mode": whiteboard_mode,
                    "selected_record_id": selected_record_id,
                    "preserve_selected_record": preserve_selected_record,
                    "selected_record_reason": selected_record_reason,
                    "pending_workspace_update": pending_workspace_update,
                    "workspace_scope": workspace_scope,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _next_trace_path(self) -> Path:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        base = self.traces_dir / f"chat-turn-{timestamp}.json"
        if not base.exists():
            return base
        index = 2
        while True:
            candidate = self.traces_dir / f"chat-turn-{timestamp}-{index}.json"
            if not candidate.exists():
                return candidate
            index += 1

    def _created_record_payload(self, executed_action: ExecutedAction | None) -> dict[str, Any] | None:
        if not executed_action or not executed_action.record_id:
            return None
        record = _find_record(
            executed_action.record_id,
            self.concept_store,
            self.memory_store,
            self.artifact_store,
        )
        if record is None:
            return None
        scope = "experiment" if "experiments" in record.path.parts else "durable"
        durability = "temporary" if scope == "experiment" else "durable"
        metadata = record.metadata if isinstance(getattr(record, "metadata", {}), dict) else {}
        explicit_revision_parent = str(metadata.get("revision_of", "") or "").strip() or None
        inferred_revision_parent = record.comes_from[0] if record.comes_from else None
        revision_parent_id = explicit_revision_parent or (
            inferred_revision_parent
            if record.source == "concept" and record.comes_from and bool(re.search(r"--v\d+$", record.id))
            else None
        )
        payload = {
            "id": record.id,
            "title": record.title,
            "type": record.type,
            "card": record.card,
            "body": record.body,
            "status": record.status,
            "kind": _record_kind(record.source, record.type),
            "memory_role": _memory_role(record.source, record.type),
            "recall_status": "learned",
            "source_tier": _source_tier(record.source, record.type),
            "links_to": record.links_to,
            "comes_from": record.comes_from,
            "derived_from_id": record.comes_from[0] if record.comes_from else None,
            "revision_parent_id": revision_parent_id,
            "lineage_kind": "revision" if revision_parent_id else ("provenance" if record.comes_from else "none"),
            "source": record.source,
            "scope": scope,
            "durability": durability,
            "why_learned": _learned_reason(record, revision_parent_id=revision_parent_id),
            "correction_affordance": _correction_affordance(record),
        }
        payload.update(artifact_lifecycle_card_fields(record))
        return payload

    def _memory_trace_payload(self, record: Any | None) -> dict[str, Any] | None:
        if record is None:
            return None
        scope = "experiment" if "experiments" in record.path.parts else "durable"
        payload = {
            "id": record.id,
            "title": record.title,
            "type": record.type,
            "card": record.card,
            "body": record.body,
            "status": record.status,
            "kind": "memory_trace",
            "memory_role": "turn_continuity",
            "recall_status": "logged",
            "source_tier": "recent",
            "links_to": record.links_to,
            "comes_from": record.comes_from,
            "source": record.source,
            "source_label": "Memory Trace",
            "scope": scope,
        }
        payload.update(parse_memory_trace_metadata(record))
        return payload


def _fallback_draft_request(
    *,
    message: str,
    pending_workspace_update: dict[str, Any] | None,
) -> str:
    if isinstance(pending_workspace_update, dict):
        origin = str(pending_workspace_update.get("origin_user_message") or "").strip()
        if origin:
            return origin
    return message


def _verification_payload(verification: ReplyVerification | None) -> dict[str, Any] | None:
    if verification is None:
        return None
    return {
        "ok": verification.ok,
        "repair_strategy": verification.repair_strategy,
        "issues": list(verification.issues),
        "retry_instruction": verification.retry_instruction,
    }


def _stage_audit_progress_message(audit: StageAuditResult) -> str:
    if audit.accepted:
        return "The response matched the requested surface."
    if audit.retryable:
        return "The response missed the requested surface, so Vantage is trying once more."
    return "The response could not be safely repaired on this turn."


def _enforce_workspace_draft_constraints(
    *,
    message: str,
    draft: WorkspaceDraft,
    workspace: WorkspaceDocument,
    vetted_memory: list[CandidateMemory],
) -> WorkspaceDraft:
    content = draft.content
    signature = _extract_known_signature(workspace=workspace, vetted_memory=vetted_memory)
    if signature:
        content = _preserve_known_signature_placeholders(content, signature)
    lowered = message.lower()
    if re.search(r"\b(no|without|remove|avoid|do not use|don't use)\s+(?:any\s+)?(?:em\s+)?dashes?\b", lowered) or "em dash" in lowered:
        content = _remove_em_dashes(content)
    if "short optional reading" in lowered or "brief optional reading" in lowered:
        content = _shorten_optional_reading_section(content)
    if content == draft.content:
        return draft
    return WorkspaceDraft(content=content, summary=draft.summary)


SIGNATURE_RE = re.compile(
    r"(?im)^\s*(?:best|thanks|thank you|regards|warmly|sincerely|cheers),?\s*\n\s*(?P<name>[A-Z][A-Za-z .'-]{1,60})\s*$"
)
SIGNATURE_PLACEHOLDER_RE = re.compile(r"\[(?:your\s+name|name)\]", re.IGNORECASE)


def _extract_known_signature(
    *,
    workspace: WorkspaceDocument,
    vetted_memory: list[CandidateMemory],
) -> str | None:
    sources = [workspace.content]
    for item in vetted_memory:
        sources.append(item.body)
        sources.append(item.card)
    for source in sources:
        signature = _extract_signature_from_text(source)
        if signature:
            return signature
    return None


def _extract_signature_from_text(text: str | None) -> str | None:
    if not text:
        return None
    for match in SIGNATURE_RE.finditer(text):
        name = match.group("name").strip()
        if "[" in name or "]" in name:
            continue
        words = name.split()
        if 1 <= len(words) <= 4:
            return name
    return None


def _preserve_known_signature_placeholders(content: str, signature: str) -> str:
    if not SIGNATURE_PLACEHOLDER_RE.search(content):
        return content
    return SIGNATURE_PLACEHOLDER_RE.sub(signature, content)


def _remove_em_dashes(content: str) -> str:
    content = content.replace("—", ", ").replace("–", ", ")
    content = re.sub(r" {2,}", " ", content)
    content = re.sub(r" ,", ",", content)
    return content


def _shorten_optional_reading_section(content: str) -> str:
    marker = re.search(r"(?im)^(?:\s*-{3,}\s*)?(?:#{1,4}\s*)?(?:\*\*)?optional reading[^\n]*(?:\*\*)?\s*$", content)
    if marker is None:
        return content
    section_start = marker.end()
    section = content[section_start:].strip()
    words = re.findall(r"\S+", section)
    if len(words) <= 90:
        return content
    sentences = re.split(r"(?<=[.!?])\s+", section)
    summary = " ".join(sentence.strip() for sentence in sentences[:2] if sentence.strip())
    if not summary or len(re.findall(r"\S+", summary)) > 80:
        summary = " ".join(words[:70])
    summary = summary.strip()
    return f"{content[:section_start].rstrip()}\n\n{summary}\n"


def _can_make_fallback_draft(
    *,
    message: str,
    workspace: WorkspaceDocument,
    pending_workspace_update: dict[str, Any] | None,
) -> bool:
    if isinstance(pending_workspace_update, dict) and str(pending_workspace_update.get("origin_user_message") or "").strip():
        return True
    lowered = message.lower()
    if not _looks_like_work_product_request(lowered):
        return False
    if not workspace.content.strip():
        return True
    if re.search(r"\b(new|fresh|separate|standalone|different)\b", lowered):
        return True
    if _looks_like_revision_request(lowered):
        return False
    return True


def _looks_like_work_product_request(lowered_message: str) -> bool:
    return bool(
        re.search(r"\b(draft|write|create|compose|open|make|generate)\b", lowered_message)
        and re.search(
            r"\b(email|essay|memo|plan|outline|checklist|agenda|itinerary|paper|letter|proposal|doc|document)\b",
            lowered_message,
        )
    )


def _looks_like_revision_request(lowered_message: str) -> bool:
    return bool(re.search(r"\b(revise|update|edit|alter|change|shorten|expand|rewrite|add|remove|make it|make the)\b", lowered_message))


def _fallback_offer_summary(message: str) -> str:
    if re.search(r"\bemail\b", message, re.IGNORECASE):
        return "Whiteboard ready for collaboratively drafting the email."
    if re.search(r"\bessay\b", message, re.IGNORECASE):
        return "Whiteboard ready for collaboratively drafting the essay."
    return "Whiteboard ready for collaboratively drafting this work product."


def _fallback_workspace_draft(message: str) -> str:
    if re.search(r"\bemail\b", message, re.IGNORECASE):
        return _fallback_email_draft(message)
    if re.search(r"\bessay\b", message, re.IGNORECASE):
        return _fallback_essay_draft(message)
    title = _fallback_title(message, fallback="Whiteboard Draft")
    return (
        f"# {title}\n\n"
        "## Goal\n\n"
        f"{_clean_fallback_sentence(message)}\n\n"
        "## Draft\n\n"
        "- Main point to refine\n"
        "- Supporting detail to fill in\n"
        "- Next step to confirm\n"
    )


def _fallback_email_draft(message: str) -> str:
    recipient = _extract_email_recipient(message) or "there"
    organization = _extract_email_organization(message)
    topic = _extract_email_topic(message) or "Following up"
    heading = f"Email Draft To {recipient.title() if recipient != 'there' else 'Recipient'}"
    if organization:
        heading += f" At {organization}"
    subject = _title_case_compact(topic, fallback="Following Up")
    greeting = f"Hi {recipient}," if recipient != "there" else "Hi,"
    body_line = _clean_fallback_sentence(topic)
    return (
        f"# {heading}\n\n"
        f"Subject: {subject}\n\n"
        f"{greeting}\n\n"
        f"{body_line}\n\n"
        "I wanted to share this clearly and keep it easy to respond to. If now is not the right time, no worries at all.\n\n"
        "Best,\n"
        "[Your Name]\n"
    )


def _fallback_essay_draft(message: str) -> str:
    title = _extract_titled_phrase(message) or _fallback_title(message, fallback="Essay Draft")
    return (
        f"# {title}\n\n"
        "This essay explores the idea from the prompt and gives it a simple structure for revision.\n\n"
        "The core argument is that early product work improves when real users help shape the product before it is treated as finished. A focused beta gives the team concrete reactions, specific workflow examples, and a clearer sense of what should change next.\n\n"
        "Using Vantage as the example, design partners can reveal where the product feels useful, where it feels confusing, and which parts of the experience matter most in real work. That makes the feedback more practical than abstract opinions or broad public reactions.\n\n"
        "The tradeoff is that design partners require care, coordination, and follow-through. The benefit is a tighter learning loop: the product can improve through real collaboration before a wider launch.\n"
    )


def _extract_email_recipient(message: str) -> str | None:
    match = re.search(r"\bto\s+([A-Z][A-Za-z'-]+)", message)
    if match:
        return match.group(1)
    return None


def _extract_email_organization(message: str) -> str | None:
    match = re.search(r"\b(?:at|from)\s+([A-Z][A-Za-z0-9&' -]+?)(?:\s+about|\s+thanking|\s+asking|[,.]|$)", message)
    if match:
        return " ".join(match.group(1).split())
    return None


def _extract_email_topic(message: str) -> str | None:
    match = re.search(r"\b(?:about|thanking|asking)\s+(.+?)(?:\s+This should\b|$)", message, re.IGNORECASE)
    if match:
        return " ".join(match.group(1).strip(" .").split())
    return None


def _extract_titled_phrase(message: str) -> str | None:
    match = re.search(r"\btitled\s+(.+?)(?:\.|$)", message, re.IGNORECASE)
    if match:
        return _title_case_compact(match.group(1).strip(" \"'"), fallback="Essay Draft")
    return None


def _fallback_title(message: str, *, fallback: str) -> str:
    compact = " ".join(message.strip().split())
    compact = re.sub(r"^(please\s+)?(try again( now)?\s*:\s*)?", "", compact, flags=re.IGNORECASE)
    compact = re.sub(r"^(open|create|draft|write|compose|make|generate)\s+(a|an|the)?\s*", "", compact, flags=re.IGNORECASE)
    return _title_case_compact(compact[:80], fallback=fallback)


def _title_case_compact(text: str, *, fallback: str) -> str:
    words = re.findall(r"[A-Za-z0-9']+", text)
    if not words:
        return fallback
    return " ".join(word.capitalize() for word in words[:10])


def _clean_fallback_sentence(text: str) -> str:
    compact = " ".join(text.strip().split())
    compact = compact.strip(" .")
    if not compact:
        return "Draft content to refine."
    return compact[0].upper() + compact[1:] + "."


def _learned_reason(
    record: Any,
    *,
    revision_parent_id: str | None,
) -> str:
    if getattr(record, "source", None) == "concept":
        if getattr(record, "type", None) == "protocol":
            return "Updated a reusable protocol so future matching requests can follow the user's preferred workflow."
        if revision_parent_id:
            return "Saved as a revision of an existing concept so the updated version stays inspectable."
        return "Captured as reusable concept knowledge."
    if getattr(record, "source", None) == "memory":
        return "Saved as memory because the user asked Vantage to remember it."
    if getattr(record, "source", None) == "artifact":
        lifecycle = artifact_lifecycle_kind(record)
        if lifecycle == "comparison_hub":
            return "Saved as a Scenario Lab comparison hub so the branch comparison can be revisited."
        if lifecycle == "whiteboard_snapshot":
            return "Saved as a whiteboard snapshot so the in-progress draft stays inspectable."
        if lifecycle == "promoted_artifact":
            return "Promoted the whiteboard into a durable artifact."
        return "Saved as a durable artifact."
    return "Saved as durable knowledge."


def _correction_affordance(record: Any) -> dict[str, str]:
    if getattr(record, "type", None) == "protocol":
        return {
            "kind": "edit_protocol",
            "label": "Edit protocol",
        }
    return {
        "kind": "open_in_whiteboard",
        "label": "Open in whiteboard",
    }


def _normalize_memory_mode(memory_intent: str | None) -> str:
    if memory_intent == "remember":
        return "remember"
    if memory_intent in {"skip", "dont_save"}:
        return "dont_save"
    return "auto"


def _trace_preserved_context_payload(candidate: CandidateMemory | None) -> dict[str, Any] | None:
    if candidate is None:
        return None
    return {
        "id": candidate.id,
        "title": candidate.title,
        "source": candidate.source,
    }


def _trace_referenced_record_payload(
    *,
    vetted_memory: list[CandidateMemory],
    selected_memory: CandidateMemory | None,
) -> dict[str, Any] | None:
    if selected_memory is not None:
        return _trace_preserved_context_payload(selected_memory)
    reopenable = [
        candidate
        for candidate in vetted_memory
        if candidate.source != "vault_note" and candidate.type != "protocol"
    ]
    if len(reopenable) != 1:
        return None
    return _trace_preserved_context_payload(reopenable[0])


def _normalize_whiteboard_mode(whiteboard_mode: str | None) -> str:
    if whiteboard_mode in {"offer", "draft", "chat"}:
        return whiteboard_mode
    return "auto"


def _graph_action_payload(
    executed_action: ExecutedAction | None,
    meta: MetaDecision,
) -> dict[str, Any] | None:
    if executed_action:
        return {
            "type": executed_action.action,
            "status": executed_action.status,
            "summary": executed_action.summary,
            "record_id": executed_action.record_id,
            "concept_id": executed_action.concept_id,
            "workspace_id": executed_action.workspace_id,
            "source": executed_action.source,
            "record_title": executed_action.record_title,
            "concept_title": executed_action.record_title,
            "rationale": meta.rationale,
        }
    if meta.action == "no_op":
        return None
    return {
        "type": meta.action,
        "status": "planned",
        "summary": meta.rationale,
        "record_id": meta.target_concept_id,
        "concept_id": meta.target_concept_id,
        "workspace_id": None,
        "source": None,
        "record_title": meta.title,
        "concept_title": meta.title,
        "rationale": meta.rationale,
    }


def _auto_graph_action_payload(executed_action: ExecutedAction | None) -> dict[str, Any] | None:
    if not executed_action:
        return None
    return {
        "type": executed_action.action,
        "status": executed_action.status,
        "summary": executed_action.summary,
        "record_id": executed_action.record_id,
        "concept_id": executed_action.concept_id,
        "workspace_id": executed_action.workspace_id,
        "source": executed_action.source,
        "record_title": executed_action.record_title,
        "concept_title": executed_action.record_title,
        "rationale": executed_action.summary,
    }


def _merge_records(*record_lists: list[Any]) -> list[Any]:
    merged: dict[tuple[str, str], Any] = {}
    for records in record_lists:
        for record in records:
            merged[(record.source, record.id)] = record
    return list(merged.values())


def _merge_saved_records(*record_lists: list[Any]) -> list[Any]:
    return _merge_records(*record_lists)


def _find_record(record_id: str, *stores: Any) -> Any | None:
    for store in stores:
        if store is None:
            continue
        try:
            return store.get(record_id)
        except FileNotFoundError:
            continue
    return None


def _extract_workspace_signal(
    response_text: str,
    *,
    whiteboard_mode: str,
) -> tuple[str, WorkspaceDraft | None, WorkspaceOffer | None]:
    text = response_text.strip()
    if not text:
        return "", None, None
    parsed_signal = _parse_workspace_labels(text)
    if parsed_signal is None:
        return text, None, None

    chat_response, signal_label, signal_body = parsed_signal
    if signal_label == "WHITEBOARD_DRAFT":
        chat_response = chat_response or "I drafted the detailed answer into the whiteboard so we can refine it there."
        if whiteboard_mode == "chat":
            return chat_response, None, None
        if whiteboard_mode == "offer":
            if "whiteboard" not in chat_response.lower() or "?" not in chat_response:
                chat_response = "This looks like a concrete draft. Want me to open the whiteboard so we can work on it together?"
            return chat_response, None, WorkspaceOffer(
                summary="Whiteboard ready for collaboratively drafting this work product.",
            )
        draft_content = _normalize_workspace_draft_content(signal_body)
        if not draft_content:
            return chat_response, None, None
        return chat_response, WorkspaceDraft(
            content=draft_content,
            summary="Drafted the detailed answer into the whiteboard for collaborative editing.",
        ), None
    if signal_label == "WHITEBOARD_OFFER":
        chat_response = chat_response or "This looks like a work product. Want me to pull up a whiteboard for it?"
        if whiteboard_mode == "chat":
            return chat_response, None, None
        offer_summary = " ".join(signal_body.strip().split())
        if not offer_summary:
            offer_summary = "Whiteboard available for collaborative drafting."
        return chat_response, None, WorkspaceOffer(summary=offer_summary)
    return chat_response or text, None, None


def _parse_workspace_labels(text: str) -> tuple[str, str | None, str] | None:
    matches = list(WHITEBOARD_LABEL_RE.finditer(text))
    if not matches:
        return None

    chat_response: str | None = None
    signal_label: str | None = None
    signal_body = ""

    for index, match in enumerate(matches):
        label = match.group("label").upper()
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():next_start].strip()
        if label == "CHAT_RESPONSE" and chat_response is None:
            chat_response = body
            continue
        if label in {"WHITEBOARD_OFFER", "WHITEBOARD_DRAFT"} and signal_label is None:
            signal_label = label
            signal_body = body
            if chat_response is None:
                chat_response = text[:match.start()].strip()

    if signal_label is None:
        return (chat_response or _strip_workspace_labels(text), None, "")
    return (chat_response or "", signal_label, signal_body)


def _strip_workspace_labels(text: str) -> str:
    return WHITEBOARD_LABEL_RE.sub("", text).strip()


def _normalize_workspace_draft_content(text: str) -> str:
    stripped = text.strip()
    fence_match = re.match(r"^```(?:markdown|md)?\s*(?P<body>.*?)\s*```$", stripped, re.DOTALL)
    if fence_match is not None:
        stripped = fence_match.group("body").strip()
    return stripped


def _workspace_title_from_content(workspace_id: str, content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return workspace_id.replace("-", " ").title()


def _merge_candidate_memory(
    first: list[CandidateMemory],
    second: list[CandidateMemory],
    *,
    limit: int,
) -> list[CandidateMemory]:
    merged: dict[tuple[str, str], CandidateMemory] = {}
    for item in [*first, *second]:
        key = (item.source, item.id)
        existing = merged.get(key)
        if existing is None or item.score >= existing.score:
            merged[key] = item
    ordered = sorted(
        merged.values(),
        key=lambda item: (item.score, _candidate_source_priority(item.source)),
        reverse=True,
    )
    return ordered[:limit]


def _candidate_source_priority(source: str) -> int:
    return {
        "concept": 3,
        "memory": 2,
        "memory_trace": 2,
        "artifact": 2,
        "vault_note": 1,
    }.get(source, 0)


def _record_kind(source: str, record_type: str) -> str:
    if record_type == "protocol":
        return "protocol"
    if source == "concept":
        return "concept"
    if source == "memory_trace":
        return "memory_trace"
    if source in {"memory", "artifact"}:
        return "saved_note"
    if source == "vault_note":
        return "reference_note"
    return "record"


def _memory_role(source: str, record_type: str) -> str:
    if record_type == "protocol":
        return "protocol"
    if source == "concept":
        return "semantic_knowledge"
    if source == "memory_trace":
        return "turn_continuity"
    if source in {"memory", "artifact"}:
        return "saved_context"
    if source == "vault_note":
        return "reference_context"
    return "context"


def _source_tier(source: str, record_type: str) -> str:
    if record_type == "protocol":
        return "instruction"
    if source == "concept":
        return "curated"
    if source == "memory_trace":
        return "recent"
    if source in {"memory", "artifact"}:
        return "saved"
    if source == "vault_note":
        return "reference"
    return "unknown"
