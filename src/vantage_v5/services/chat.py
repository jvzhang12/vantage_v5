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

WHITEBOARD_DRAFT_RE = re.compile(
    r"^\s*CHAT_RESPONSE:\s*(?P<chat>.*?)\n+WHITEBOARD_DRAFT:\s*(?P<draft>.+?)\s*$",
    re.DOTALL,
)
WHITEBOARD_OFFER_RE = re.compile(
    r"^\s*CHAT_RESPONSE:\s*(?P<chat>.*?)\n+WHITEBOARD_OFFER:\s*(?P<offer>.+?)\s*$",
    re.DOTALL,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkspaceDraft:
    content: str
    summary: str


@dataclass(slots=True)
class WorkspaceOffer:
    summary: str


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
        if self.client:
            try:
                assistant_reply = self._openai_reply(
                    message=message,
                    workspace=workspace,
                    history=history,
                    vetted_memory=vetted_memory,
                    selected_memory=selected_memory if preserve_selected_memory else None,
                    whiteboard_mode=whiteboard_mode,
                    pending_workspace_update=pending_workspace_update,
                )
            except Exception:
                logger.exception("OpenAI chat reply failed; falling back to deterministic chat response.")
                assistant_message = self._fallback_reply(
                    message=message,
                    workspace=workspace,
                    vetted_memory=vetted_memory,
                    fallback_reason="provider_error",
                )
                workspace_draft = None
                workspace_offer = None
                mode = "fallback"
            else:
                assistant_message, workspace_draft, workspace_offer = _extract_workspace_signal(
                    assistant_reply,
                    whiteboard_mode=whiteboard_mode,
                )
                mode = "openai"
        else:
            assistant_message = self._fallback_reply(
                message=message,
                workspace=workspace,
                vetted_memory=vetted_memory,
            )
            workspace_draft = None
            workspace_offer = None
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
        }
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
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
                "For that invitation, respond exactly in this format: "
                "CHAT_RESPONSE: <one or two sentences asking whether the user wants to pull up a whiteboard for this work product> "
                "WHITEBOARD_OFFER: <one sentence describing what could be drafted in the whiteboard>. "
                "When the user has already chosen the whiteboard or clearly wants collaborative drafting there, respond exactly in this format: "
                "CHAT_RESPONSE: <one to three sentences telling the user the detailed draft is now in the whiteboard> "
                "WHITEBOARD_DRAFT: <complete Markdown draft beginning with a level-one heading>. "
                "The whiteboard draft should contain the full structured content and should be ready for collaborative editing. "
                "Use these special formats only for concrete work products and whiteboard collaboration. "
                "Otherwise, respond normally with just the assistant message."
            ),
            input=json.dumps(input_payload),
        )
        return response.output_text.strip()

    @staticmethod
    def _fallback_reply(
        *,
        message: str,
        workspace: WorkspaceDocument,
        vetted_memory: list[CandidateMemory],
        fallback_reason: str = "no_openai_key",
    ) -> str:
        concept_titles = [item.title for item in vetted_memory if item.source == "concept"]
        trace_titles = [item.title for item in vetted_memory if item.source == "memory_trace"]
        saved_note_titles = [item.title for item in vetted_memory if item.source in {"memory", "artifact"}]
        vault_titles = [item.title for item in vetted_memory if item.source == "vault_note"]
        memory_summary = ""
        if concept_titles or trace_titles or saved_note_titles or vault_titles:
            parts: list[str] = []
            if concept_titles:
                parts.append(f"Relevant concepts: {', '.join(concept_titles)}.")
            if trace_titles:
                parts.append(f"Relevant memory trace: {', '.join(trace_titles)}.")
            if saved_note_titles:
                parts.append(f"Relevant saved notes: {', '.join(saved_note_titles)}.")
            if vault_titles:
                parts.append(f"Relevant reference notes: {', '.join(vault_titles)}.")
            memory_summary = " " + " ".join(parts)
        fallback_status = "Fallback mode is active because no OpenAI key is configured."
        if fallback_reason == "provider_error":
            fallback_status = "Fallback mode is active because the model provider was unavailable for this turn."
        return (
            f"You said: {message}\n\n"
            f"The active workspace is '{workspace.title}'. "
            f"{fallback_status} "
            "I can still help you think through the document and suggest changes based on the current workspace."
            f"{memory_summary}"
        )

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
            "correction_affordance": {
                "kind": "open_in_whiteboard",
                "label": "Open in whiteboard",
            },
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
    reopenable = [candidate for candidate in vetted_memory if candidate.source != "vault_note"]
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
    draft_match = WHITEBOARD_DRAFT_RE.match(text)
    if draft_match is not None:
        chat_response = draft_match.group("chat").strip() or "I drafted the detailed answer into the whiteboard so we can refine it there."
        if whiteboard_mode == "chat":
            return chat_response, None, None
        if whiteboard_mode == "offer":
            if "whiteboard" not in chat_response.lower() or "?" not in chat_response:
                chat_response = "This looks like a concrete draft. Want me to open the whiteboard so we can work on it together?"
            return chat_response, None, WorkspaceOffer(
                summary="Whiteboard ready for collaboratively drafting this work product.",
            )
        draft_content = _normalize_workspace_draft_content(draft_match.group("draft"))
        if not draft_content:
            return chat_response, None, None
        return chat_response, WorkspaceDraft(
            content=draft_content,
            summary="Drafted the detailed answer into the whiteboard for collaborative editing.",
        ), None
    offer_match = WHITEBOARD_OFFER_RE.match(text)
    if offer_match is not None:
        chat_response = offer_match.group("chat").strip() or "This looks like a work product. Want me to pull up a whiteboard for it?"
        if whiteboard_mode == "chat":
            return chat_response, None, None
        offer_summary = " ".join(offer_match.group("offer").strip().split())
        if not offer_summary:
            offer_summary = "Whiteboard available for collaborative drafting."
        return chat_response, None, WorkspaceOffer(summary=offer_summary)
    return text, None, None


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
