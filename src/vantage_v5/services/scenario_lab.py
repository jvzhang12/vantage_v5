from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from openai import OpenAI

from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.response_mode import build_response_mode_payload
from vantage_v5.services.response_mode import finalize_assistant_message
from vantage_v5.services.search import CandidateMemory
from vantage_v5.services.search import ConceptSearchService
from vantage_v5.services.search import tokenize
from vantage_v5.services.vetting import anchor_selected_record_candidate
from vantage_v5.services.vetting import build_continuity_hint
from vantage_v5.services.vetting import resolve_selected_record_candidate
from vantage_v5.services.vetting import should_preserve_selected_record
from vantage_v5.services.vetting import ConceptVettingService
from vantage_v5.storage.artifacts import ArtifactRecord
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.artifacts import parse_artifact_scenario_metadata
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.markdown_store import slugify
from vantage_v5.storage.memory_trace import MemoryTraceStore
from vantage_v5.storage.memories import MemoryStore
from vantage_v5.storage.vault import VaultNoteStore
from vantage_v5.storage.workspaces import inject_scenario_metadata
from vantage_v5.storage.workspaces import WorkspaceDocument
from vantage_v5.storage.workspaces import WorkspaceStore

FOLLOW_UP_CUES = (
    "what about",
    "which one",
    "the first",
    "the second",
    "the third",
    "that one",
    "this one",
    "those",
    "these",
    "compare that",
    "compare it",
    "compare",
    "recommend",
    "recommendation",
    "tradeoff",
    "tradeoffs",
    "risk",
    "risks",
    "elaborate",
    "expand",
    "go deeper",
    "tell me more",
    "same one",
    "baseline",
    "rerun",
    "again",
)


@dataclass(slots=True)
class ScenarioBranchPlan:
    label: str
    title: str
    preserved_assumptions: list[str]
    changed_assumptions: list[str]
    first_order_effects: list[str]
    second_order_effects: list[str]
    risks: list[str]
    open_questions: list[str]
    confidence: str
    card: str = ""


@dataclass(slots=True)
class ScenarioComparisonPlan:
    title: str
    summary: str
    tradeoffs: list[str]
    recommendation: str
    next_steps: list[str]


@dataclass(slots=True)
class ScenarioPlan:
    comparison_question: str
    shared_context_summary: str
    shared_assumptions: list[str]
    branches: list[ScenarioBranchPlan]
    comparison: ScenarioComparisonPlan


@dataclass(slots=True)
class ScenarioLabTurn:
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
    created_record: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        created_record = self.created_record or (self.learned[0] if self.learned else None)
        selected_memory = _group_memory_payload(self.saved_notes, self.vault_notes)
        candidate_memory = _group_memory_payload(self.candidate_saved_notes, self.candidate_vault_notes)
        return {
            "user_message": self.user_message,
            "assistant_message": self.assistant_message,
            "workspace": {
                "workspace_id": self.workspace_id,
                "title": self.workspace_title,
                "content": self.workspace_content,
            },
            "memory": selected_memory,
            "selected_memory": selected_memory,
            "candidate_memory": candidate_memory,
            "concept_cards": self.concept_cards,
            "saved_notes": self.saved_notes,
            "vault_notes": self.vault_notes,
            "turn_vault_notes": self.vault_notes,
            "candidate_concepts": self.candidate_concepts,
            "candidate_saved_notes": self.candidate_saved_notes,
            "candidate_vault_notes": self.candidate_vault_notes,
            "candidate_memory_results": self.candidate_memory,
            "recall": self.working_memory,
            "working_memory": self.working_memory,
            "learned": self.learned,
            "memory_trace_record": self.memory_trace_record,
            "response_mode": self.response_mode,
            "vetting": self.vetting,
            "mode": "scenario_lab",
            "meta_action": {
                "action": "no_op",
                "rationale": "Scenario Lab writes branch workspaces and a comparison artifact outside the normal memory loop.",
            },
            "graph_action": None,
            "created_record": created_record,
            "scenario_lab": {
                "navigator": self.navigator,
                "question": self.comparison_question,
                "comparison_question": self.comparison_question,
                "summary": self.comparison_artifact.get("card") or self.assistant_message,
                "recommendation": self.comparison_artifact.get("recommendation"),
                "branches": self.branches,
                "comparison_artifact": self.comparison_artifact,
            },
        }


class ScenarioLabService:
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
        self.traces_dir = traces_dir
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None

    def run(
        self,
        *,
        message: str,
        workspace: WorkspaceDocument,
        history: list[dict[str, str]],
        navigation: NavigationDecision,
        selected_record_id: str | None = None,
        pending_workspace_update: dict[str, Any] | None = None,
    ) -> ScenarioLabTurn:
        if not self.client:
            raise RuntimeError("Scenario Lab requires OpenAI mode.")

        concepts = _merge_records(
            self.concept_store.list_concepts(),
            self.reference_concept_store.list_concepts() if self.reference_concept_store else [],
        )
        saved_notes = _merge_records(
            self.memory_store.list_memories(),
            self.artifact_store.list_artifacts(),
            self.reference_memory_store.list_memories() if self.reference_memory_store else [],
            self.reference_artifact_store.list_artifacts() if self.reference_artifact_store else [],
        )
        memory_traces = _merge_records(
            self.memory_trace_store.list_recent_traces(),
            self.reference_memory_trace_store.list_recent_traces() if self.reference_memory_trace_store else [],
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
        )
        preserve_selected_memory = navigation.preserve_selected_record
        if preserve_selected_memory is None:
            preserve_selected_memory = should_preserve_selected_record(
                message=message,
                history=history,
                selected_memory=selected_memory,
            )
        continuity_hint = build_continuity_hint(
            message=message,
            history=history,
            selected_memory=selected_memory,
            preserve_selected_record=preserve_selected_memory,
            selected_record_reason=navigation.selected_record_reason,
            pending_workspace_update=pending_workspace_update,
            workspace=workspace,
            workspace_scope="visible" if workspace.content.strip() else "excluded",
        )
        candidate_memory = self.search_service.search_context(
            query=message,
            memory_trace_records=memory_traces,
            concept_records=concepts,
            saved_note_records=saved_notes,
            vault_records=vault_notes,
            limit=16,
        )
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
                continuity_reason=navigation.selected_record_reason,
            )
        vetted_concepts = [item for item in vetted_memory if item.source == "concept"]
        vetted_saved_notes = [item for item in vetted_memory if item.source in {"memory", "artifact"}]
        vetted_vault_notes = [item for item in vetted_memory if item.source == "vault_note"]
        candidate_concepts = [item for item in candidate_memory if item.source == "concept"]
        candidate_saved_notes = [item for item in candidate_memory if item.source in {"memory", "artifact"}]
        candidate_vault_notes = [item for item in candidate_memory if item.source == "vault_note"]
        selected_record = selected_memory if preserve_selected_memory else None
        selected_record_payload = self._build_selected_record_payload(selected_record)

        scenario_plan = self._openai_build_scenario(
            message=message,
            workspace=workspace,
            history=history,
            vetted_memory=vetted_memory,
            navigation=navigation,
            selected_record=selected_record,
            selected_record_payload=selected_record_payload,
            pending_workspace_update=pending_workspace_update,
        )
        response_mode = build_response_mode_payload(
            vetted_memory,
            workspace_has_context=bool(workspace.content.strip()),
            history_has_context=bool(history),
            pending_workspace_has_context=bool(pending_workspace_update),
        )
        saved_branches: list[dict[str, Any]] = []
        comparison_artifact: ArtifactRecord | None = None
        persisted_paths: list[Path] = []
        try:
            scenario_namespace_id, namespace_mode = _scenario_namespace(
                base_workspace=workspace,
                scenario_plan=scenario_plan,
            )
            comparison_title = _neutral_comparison_title(
                comparison_question=scenario_plan.comparison_question,
                suggested_title=scenario_plan.comparison.title,
            )
            comparison_artifact_title = comparison_title or f"{workspace.title} Scenario Comparison"
            comparison_artifact_id = self.artifact_store.preview_artifact_id(
                comparison_artifact_title,
                record_type="scenario_comparison",
            )
            saved_branches = self._save_branches(
                workspace=workspace,
                scenario_plan=scenario_plan,
                scenario_namespace_id=scenario_namespace_id,
                namespace_mode=namespace_mode,
                comparison_artifact_id=comparison_artifact_id,
            )
            persisted_paths.extend(self.workspace_store.workspaces_dir / f"{branch['workspace_id']}.md" for branch in saved_branches)
            comparison_artifact = self._save_comparison_artifact(
                workspace=workspace,
                scenario_plan=scenario_plan,
                branch_workspace_ids=[branch["workspace_id"] for branch in saved_branches],
                related_concepts=[item.id for item in vetted_concepts[:3]],
                comparison_title=comparison_artifact_title,
                comparison_artifact_id=comparison_artifact_id,
                scenario_namespace_id=scenario_namespace_id,
                namespace_mode=namespace_mode,
            )
            persisted_paths.append(comparison_artifact.path)
            created_record = _record_payload(comparison_artifact)
            memory_trace_record = self.memory_trace_store.create_turn_trace(
                user_message=message,
                assistant_message=(
                    f"I created {len(saved_branches)} scenario branches and a comparison artifact. "
                    f"{scenario_plan.comparison.summary.strip()}"
                ).strip(),
                working_memory=[candidate.to_dict() for candidate in vetted_memory],
                history=history,
                workspace_id=workspace.workspace_id,
                workspace_title=workspace.title,
                workspace_content=workspace.content,
                workspace_scope="visible" if workspace.content.strip() else "excluded",
                learned=[created_record],
                response_mode=response_mode,
                scope="experiment" if "experiments" in self.memory_trace_store.records_dir.parts else "durable",
                pending_workspace_update=pending_workspace_update,
            )
            assistant_message = (
                f"I created {len(saved_branches)} scenario branches and a comparison artifact. "
                f"{scenario_plan.comparison.summary.strip()}"
            ).strip()
            assistant_message = finalize_assistant_message(
                assistant_message,
                response_mode=response_mode,
            )
            turn = ScenarioLabTurn(
                user_message=message,
                assistant_message=assistant_message,
                workspace_id=workspace.workspace_id,
                workspace_title=workspace.title,
                workspace_content=None,
                concept_cards=[candidate.to_dict() for candidate in vetted_concepts],
                saved_notes=[candidate.to_dict() for candidate in vetted_saved_notes],
                vault_notes=[candidate.to_dict() for candidate in vetted_vault_notes],
                candidate_concepts=[candidate.to_dict() for candidate in candidate_concepts],
                candidate_saved_notes=[candidate.to_dict() for candidate in candidate_saved_notes],
                candidate_vault_notes=[candidate.to_dict() for candidate in candidate_vault_notes],
                candidate_memory=[candidate.to_dict() for candidate in candidate_memory],
                working_memory=[candidate.to_dict() for candidate in vetted_memory],
                learned=[created_record],
                memory_trace_record=_record_payload(memory_trace_record),
                response_mode=response_mode,
                vetting=vetting,
                navigator=navigation.to_dict(),
                comparison_question=scenario_plan.comparison_question,
                branches=saved_branches,
                comparison_artifact={
                    **created_record,
                    "recommendation": scenario_plan.comparison.recommendation,
                    "workspace_count": len(saved_branches),
                },
                created_record=created_record,
            )
            self._trace_turn(
                turn=turn,
                workspace=workspace,
                history=history,
                scenario_plan=scenario_plan,
                pending_workspace_update=pending_workspace_update,
            )
            return turn
        except Exception:
            _cleanup_paths(persisted_paths)
            raise

    def _openai_build_scenario(
        self,
        *,
        message: str,
        workspace: WorkspaceDocument,
        history: list[dict[str, str]],
        vetted_memory: list[CandidateMemory],
        navigation: NavigationDecision,
        selected_record: CandidateMemory | None,
        selected_record_payload: dict[str, Any] | None,
        pending_workspace_update: dict[str, Any] | None,
    ) -> ScenarioPlan:
        requested_count = _requested_branch_count(navigation)
        requested_labels = _requested_branch_labels(navigation, requested_count)
        payload = {
            "user_message": message,
            "comparison_question": navigation.comparison_question or message,
            "workspace": {
                "workspace_id": workspace.workspace_id,
                "title": workspace.title,
                "content": workspace.content,
            },
            "recent_chat": history[-6:],
            "selected_record_id": selected_record.id if selected_record else None,
            "selected_record": selected_record_payload,
            "vetted_memory": [item.to_dict() for item in vetted_memory],
            "pending_workspace_update": pending_workspace_update,
            "requested_branch_count": requested_count,
            "requested_branch_labels": requested_labels,
        }
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are Vantage V5 running Scenario Lab. "
                "Turn the user's question into 2 or 3 clearly differentiated scenario branches grounded in the current workspace and vetted memory. "
                "Make each branch decision-useful rather than decorative. "
                "Each branch should have a short human title, ideally 2 to 5 words, and a one-sentence thesis card. "
                "Keep assumptions explicit. "
                "If a selected record is provided, treat it as the in-focus continuity anchor for follow-up turns. "
                "If pending whiteboard context is provided, treat it as live continuity context from the immediately prior turn. "
                "Use compact, concrete language that works well in Markdown workspaces. "
                "The comparison should end with a practical recommendation and next steps."
            ),
            input=json.dumps(payload),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "scenario_plan",
                    "strict": False,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "comparison_question": {"type": "string"},
                            "shared_context_summary": {"type": "string"},
                            "shared_assumptions": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "branches": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "label": {"type": "string"},
                                        "title": {"type": "string"},
                                        "card": {"type": "string"},
                                        "preserved_assumptions": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "changed_assumptions": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "first_order_effects": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "second_order_effects": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "risks": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "open_questions": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "confidence": {"type": "string"},
                                    },
                                    "required": [
                                        "label",
                                        "title",
                                        "card",
                                        "preserved_assumptions",
                                        "changed_assumptions",
                                        "first_order_effects",
                                        "second_order_effects",
                                        "risks",
                                        "open_questions",
                                        "confidence",
                                    ],
                                },
                            },
                            "comparison": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "title": {"type": "string"},
                                    "summary": {"type": "string"},
                                    "tradeoffs": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "recommendation": {"type": "string"},
                                    "next_steps": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                                "required": [
                                    "title",
                                    "summary",
                                    "tradeoffs",
                                    "recommendation",
                                    "next_steps",
                                ],
                            },
                        },
                        "required": [
                            "comparison_question",
                            "shared_context_summary",
                            "shared_assumptions",
                            "branches",
                            "comparison",
                        ],
                    },
                }
            },
        )
        result = json.loads(response.output_text)
        branches = [
            ScenarioBranchPlan(
                label=str(item.get("label") or ""),
                title=str(item.get("title") or ""),
                card=str(item.get("card") or ""),
                preserved_assumptions=_string_list(item.get("preserved_assumptions")),
                changed_assumptions=_string_list(item.get("changed_assumptions")),
                first_order_effects=_string_list(item.get("first_order_effects")),
                second_order_effects=_string_list(item.get("second_order_effects")),
                risks=_string_list(item.get("risks")),
                open_questions=_string_list(item.get("open_questions")),
                confidence=str(item.get("confidence") or "medium"),
            )
            for item in result.get("branches", [])
        ]
        comparison = result.get("comparison") or {}
        return ScenarioPlan(
            comparison_question=str(result.get("comparison_question") or message),
            shared_context_summary=str(result.get("shared_context_summary") or ""),
            shared_assumptions=_string_list(result.get("shared_assumptions")),
            branches=branches,
            comparison=ScenarioComparisonPlan(
                title=str(comparison.get("title") or "Scenario Comparison"),
                summary=str(comparison.get("summary") or ""),
                tradeoffs=_string_list(comparison.get("tradeoffs")),
                recommendation=str(comparison.get("recommendation") or ""),
                next_steps=_string_list(comparison.get("next_steps")),
            ),
        )

    def _save_branches(
        self,
        *,
        workspace: WorkspaceDocument,
        scenario_plan: ScenarioPlan,
        scenario_namespace_id: str,
        namespace_mode: str,
        comparison_artifact_id: str,
    ) -> list[dict[str, Any]]:
        requested_count = max(2, min(3, len(scenario_plan.branches) or 3))
        branches = _normalize_branch_plans(
            scenario_plan.branches,
            requested_count=requested_count,
        )
        saved_branches: list[dict[str, Any]] = []
        persisted_paths: list[Path] = []
        try:
            for index, branch in enumerate(branches, start=1):
                branch_slug = slugify(branch.label) or f"scenario-{index}"
                workspace_id = self._unique_workspace_id(f"{scenario_namespace_id}--{branch_slug}")
                content = _render_branch_workspace(
                    base_workspace=workspace,
                    comparison_question=scenario_plan.comparison_question,
                    shared_context_summary=scenario_plan.shared_context_summary,
                    shared_assumptions=scenario_plan.shared_assumptions,
                    branch=branch,
                    scenario_namespace_id=scenario_namespace_id,
                    namespace_mode=namespace_mode,
                    comparison_artifact_id=comparison_artifact_id,
                )
                document = self.workspace_store.save(workspace_id, content)
                persisted_paths.append(document.path)
                scenario_metadata = document.scenario_metadata or {}
                saved_branches.append(
                    {
                        "workspace_id": document.workspace_id,
                        "id": document.workspace_id,
                        "title": document.title,
                        "type": "workspace branch",
                        "card": branch.card,
                        "body": content,
                        "path": document.path.name,
                        "label": branch.label,
                        "summary": branch.card,
                        "risk_summary": _first_line(branch.risks),
                        "confidence": branch.confidence,
                        "kind": "workspace_branch",
                        "status": "counterfactual",
                        "source": "workspace",
                        "scope": "experiment" if "experiments" in document.path.parts else "durable",
                        "scenario_kind": scenario_metadata.get("scenario_kind", "branch"),
                        **scenario_metadata,
                    }
                )
            return saved_branches
        except Exception:
            _cleanup_paths(persisted_paths)
            raise

    def _save_comparison_artifact(
        self,
        *,
        workspace: WorkspaceDocument,
        scenario_plan: ScenarioPlan,
        branch_workspace_ids: list[str],
        related_concepts: list[str],
        comparison_title: str,
        comparison_artifact_id: str,
        scenario_namespace_id: str,
        namespace_mode: str,
    ) -> ArtifactRecord:
        body = _render_comparison_artifact(
            base_workspace=workspace,
            scenario_plan=scenario_plan,
            comparison_title=comparison_title,
            branch_workspace_ids=branch_workspace_ids,
            comparison_artifact_id=comparison_artifact_id,
            scenario_namespace_id=scenario_namespace_id,
            namespace_mode=namespace_mode,
        )
        return self.artifact_store.create_artifact(
            record_id=comparison_artifact_id,
            title=comparison_title,
            card=_summarize_text(scenario_plan.comparison.summary, fallback=scenario_plan.comparison_question),
            body=body,
            type="scenario_comparison",
            links_to=related_concepts,
            comes_from=[workspace.workspace_id, *branch_workspace_ids],
            scenario_metadata={
                "scenario_kind": "comparison",
                "base_workspace_id": workspace.workspace_id,
                "comparison_question": scenario_plan.comparison_question,
                "comparison_artifact_id": comparison_artifact_id,
                "branch_workspace_ids": branch_workspace_ids,
                "scenario_namespace_id": scenario_namespace_id,
                "namespace_mode": namespace_mode,
            },
        )

    def _build_selected_record_payload(
        self,
        selected_record: CandidateMemory | None,
    ) -> dict[str, Any] | None:
        if selected_record is None:
            return None
        resolved_record = self._load_selected_record(selected_record)
        comes_from = list(getattr(resolved_record, "comes_from", []) or []) if resolved_record is not None else []
        return _serialize_selected_record_payload(selected_record, comes_from=comes_from)

    def _load_selected_record(self, selected_record: CandidateMemory) -> Any | None:
        if selected_record.source == "concept":
            stores = [self.concept_store, self.reference_concept_store]
        elif selected_record.source == "memory":
            stores = [self.memory_store, self.reference_memory_store]
        elif selected_record.source == "artifact":
            stores = [self.artifact_store, self.reference_artifact_store]
        else:
            return None

        for store in stores:
            if store is None:
                continue
            try:
                return store.get(selected_record.id)
            except FileNotFoundError:
                continue
        return None

    def _unique_workspace_id(self, base_workspace_id: str) -> str:
        workspace_id = base_workspace_id
        index = 2
        while (self.workspace_store.workspaces_dir / f"{workspace_id}.md").exists():
            workspace_id = f"{base_workspace_id}-{index}"
            index += 1
        return workspace_id

    def _trace_turn(
        self,
        *,
        turn: ScenarioLabTurn,
        workspace: WorkspaceDocument,
        history: list[dict[str, str]],
        scenario_plan: ScenarioPlan,
        pending_workspace_update: dict[str, Any] | None,
    ) -> None:
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        trace_path = self._next_trace_path()
        trace_path.write_text(
            json.dumps(
                {
                    "turn": turn.to_dict(),
                    "workspace_excerpt": workspace.content[:1200],
                    "history": history[-6:],
                    "pending_workspace_update": pending_workspace_update,
                    "scenario_plan": _scenario_plan_payload(scenario_plan),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _next_trace_path(self) -> Path:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        base = self.traces_dir / f"scenario-lab-turn-{timestamp}.json"
        if not base.exists():
            return base
        index = 2
        while True:
            candidate = self.traces_dir / f"scenario-lab-turn-{timestamp}-{index}.json"
            if not candidate.exists():
                return candidate
            index += 1


def _requested_branch_count(navigation: NavigationDecision) -> int:
    if navigation.branch_labels:
        return max(2, min(3, len(navigation.branch_labels)))
    if navigation.branch_count:
        return max(2, min(3, navigation.branch_count))
    return 3


def _requested_branch_labels(navigation: NavigationDecision, requested_count: int) -> list[str]:
    labels = [label.strip() for label in navigation.branch_labels if label.strip()]
    labels = labels[:requested_count]
    defaults = ["baseline", "constrained", "aggressive"]
    for label in defaults:
        if len(labels) >= requested_count:
            break
        labels.append(label)
    return labels[:requested_count]


def _normalize_branch_plans(branches: list[ScenarioBranchPlan], *, requested_count: int) -> list[ScenarioBranchPlan]:
    normalized = branches[:requested_count]
    defaults = [
        ScenarioBranchPlan(
            label="baseline",
            title="Baseline",
            card="Keeps the current path intact for comparison.",
            preserved_assumptions=[],
            changed_assumptions=[],
            first_order_effects=[],
            second_order_effects=[],
            risks=[],
            open_questions=[],
            confidence="medium",
        ),
        ScenarioBranchPlan(
            label="constrained",
            title="Constrained Path",
            card="Tightens scope to reduce risk and focus the team.",
            preserved_assumptions=[],
            changed_assumptions=[],
            first_order_effects=[],
            second_order_effects=[],
            risks=[],
            open_questions=[],
            confidence="medium",
        ),
        ScenarioBranchPlan(
            label="aggressive",
            title="Aggressive Path",
            card="Pushes for speed or reach at the cost of higher execution risk.",
            preserved_assumptions=[],
            changed_assumptions=[],
            first_order_effects=[],
            second_order_effects=[],
            risks=[],
            open_questions=[],
            confidence="medium",
        ),
    ]
    while len(normalized) < requested_count:
        normalized.append(defaults[len(normalized)])
    cleaned: list[ScenarioBranchPlan] = []
    for index, branch in enumerate(normalized, start=1):
        cleaned_title = _clean_branch_title(branch, index=index)
        cleaned_card = _clean_branch_card(branch)
        cleaned.append(
            ScenarioBranchPlan(
                label=slugify(branch.label) or f"scenario-{index}",
                title=cleaned_title,
                card=cleaned_card,
                preserved_assumptions=branch.preserved_assumptions,
                changed_assumptions=branch.changed_assumptions,
                first_order_effects=branch.first_order_effects,
                second_order_effects=branch.second_order_effects,
                risks=branch.risks,
                open_questions=branch.open_questions,
                confidence=branch.confidence.strip() or "medium",
            )
        )
    return cleaned


def _render_branch_workspace(
    *,
    base_workspace: WorkspaceDocument,
    comparison_question: str,
    shared_context_summary: str,
    shared_assumptions: list[str],
    branch: ScenarioBranchPlan,
    comparison_artifact_id: str,
    scenario_namespace_id: str,
    namespace_mode: str,
) -> str:
    sections = [
        f"# {branch.title}",
        "",
        f"Base Workspace: {base_workspace.workspace_id}",
        f"Question: {comparison_question}",
        "Status: Counterfactual Branch",
        f"Branch Label: {branch.label}",
        f"Comparison Artifact: {comparison_artifact_id}",
        f"Scenario Namespace: {scenario_namespace_id} ({namespace_mode})",
        "",
        "## Thesis",
        branch.card,
        "",
        "## Shared Context",
        shared_context_summary.strip() or "See the preserved assumptions below.",
        "",
        "## Shared Assumptions",
        _markdown_bullets(shared_assumptions, fallback="- None recorded."),
        "",
        "## Preserved Assumptions",
        _markdown_bullets(branch.preserved_assumptions, fallback="- Carry forward the current plan structure unless contradicted below."),
        "",
        "## Changed Assumptions",
        _markdown_bullets(branch.changed_assumptions, fallback="- No branch-specific changes were recorded."),
        "",
        "## Predicted First-Order Effects",
        _markdown_bullets(branch.first_order_effects, fallback="- No immediate effects were recorded."),
        "",
        "## Predicted Second-Order Effects",
        _markdown_bullets(branch.second_order_effects, fallback="- No second-order effects were recorded."),
        "",
        "## Risks",
        _markdown_bullets(branch.risks, fallback="- No material risks were recorded."),
        "",
        "## Open Questions",
        _markdown_bullets(branch.open_questions, fallback="- No open questions were recorded."),
        "",
        "## Confidence",
        branch.confidence,
        "",
    ]
    return inject_scenario_metadata(
        "\n".join(sections),
        {
            "scenario_kind": "branch",
            "base_workspace_id": base_workspace.workspace_id,
            "comparison_question": comparison_question,
            "branch_label": branch.label,
            "comparison_artifact_id": comparison_artifact_id,
            "scenario_namespace_id": scenario_namespace_id,
            "namespace_mode": namespace_mode,
        },
    )


def _render_comparison_artifact(
    *,
    base_workspace: WorkspaceDocument,
    scenario_plan: ScenarioPlan,
    comparison_title: str,
    branch_workspace_ids: list[str],
    comparison_artifact_id: str,
    scenario_namespace_id: str,
    namespace_mode: str,
) -> str:
    sections = [
        f"# {comparison_title}",
        "",
        f"Base Workspace: {base_workspace.workspace_id}",
        f"Question: {scenario_plan.comparison_question}",
        f"Comparison Artifact: {comparison_artifact_id}",
        f"Scenario Namespace: {scenario_namespace_id} ({namespace_mode})",
        "",
        "## Shared Context",
        scenario_plan.shared_context_summary.strip() or "See the shared assumptions below.",
        "",
        "## Shared Assumptions",
        _markdown_bullets(scenario_plan.shared_assumptions, fallback="- None recorded."),
        "",
        "## Branches Compared",
        _markdown_bullets(branch_workspace_ids, fallback="- No scenario branches were saved."),
        "",
        "## Summary",
        scenario_plan.comparison.summary.strip() or "No comparison summary was generated.",
        "",
        "## Tradeoffs",
        _markdown_bullets(scenario_plan.comparison.tradeoffs, fallback="- No tradeoffs were recorded."),
        "",
        "## Recommendation",
        scenario_plan.comparison.recommendation.strip() or "No recommendation was recorded.",
        "",
        "## Next Steps",
        _markdown_bullets(scenario_plan.comparison.next_steps, fallback="- No next steps were recorded."),
        "",
    ]
    return "\n".join(sections)


def _record_payload(record: ArtifactRecord) -> dict[str, Any]:
    scope = "experiment" if "experiments" in record.path.parts else "durable"
    scenario_metadata = ArtifactStore.parse_scenario_metadata(record) or {}
    payload = {
        "id": record.id,
        "title": record.title,
        "type": record.type,
        "scenario_kind": scenario_metadata.get("scenario_kind") or _scenario_kind_for_record_type(record.type),
        "card": record.card,
        "body": record.body,
        "status": record.status,
        "links_to": record.links_to,
        "comes_from": record.comes_from,
        "source": record.source,
        "source_label": "Memory Trace" if record.source == "memory_trace" else "Saved artifact",
        "scope": scope,
        "filename": record.path.name,
    }
    payload.update(scenario_metadata)
    return payload


def _group_memory_payload(
    saved_notes: list[dict[str, Any]],
    reference_notes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "saved_notes": saved_notes,
        "reference_notes": reference_notes,
        "total": len(saved_notes) + len(reference_notes),
    }


def _merge_records(*record_lists: list[Any]) -> list[Any]:
    merged: dict[tuple[str, str], Any] = {}
    for records in record_lists:
        for record in records:
            merged[(record.source, record.id)] = record
    return list(merged.values())


def _summarize_text(text: str, *, fallback: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return fallback.strip() or "Scenario comparison"
    sentence = cleaned.split(". ", 1)[0].strip()
    summary = sentence[:160].strip()
    if not summary:
        return fallback.strip() or "Scenario comparison"
    return summary if summary.endswith(".") else f"{summary}."


def _first_line(values: list[str]) -> str:
    return values[0].strip() if values else ""


def _markdown_bullets(values: list[str], *, fallback: str) -> str:
    if not values:
        return fallback
    return "\n".join(f"- {value.strip()}" for value in values if value.strip()) or fallback


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _scenario_plan_payload(plan: ScenarioPlan) -> dict[str, Any]:
    return {
        "comparison_question": plan.comparison_question,
        "shared_context_summary": plan.shared_context_summary,
        "shared_assumptions": plan.shared_assumptions,
        "branches": [
            {
                "label": branch.label,
                "title": branch.title,
                "card": branch.card,
                "preserved_assumptions": branch.preserved_assumptions,
                "changed_assumptions": branch.changed_assumptions,
                "first_order_effects": branch.first_order_effects,
                "second_order_effects": branch.second_order_effects,
                "risks": branch.risks,
                "open_questions": branch.open_questions,
                "confidence": branch.confidence,
            }
            for branch in plan.branches
        ],
        "comparison": {
            "title": plan.comparison.title,
            "summary": plan.comparison.summary,
            "tradeoffs": plan.comparison.tradeoffs,
            "recommendation": plan.comparison.recommendation,
            "next_steps": plan.comparison.next_steps,
        },
    }


def _scenario_namespace(*, base_workspace: WorkspaceDocument, scenario_plan: ScenarioPlan) -> tuple[str, str]:
    if _matches_workspace_context(base_workspace=base_workspace, scenario_plan=scenario_plan):
        return base_workspace.workspace_id, "anchored"
    namespace = _scenario_namespace_slug(scenario_plan)
    if namespace:
        return namespace, "detached"
    return base_workspace.workspace_id, "anchored"


def _matches_workspace_context(*, base_workspace: WorkspaceDocument, scenario_plan: ScenarioPlan) -> bool:
    workspace_tokens = tokenize(f"{base_workspace.workspace_id} {base_workspace.title}")
    scenario_tokens = tokenize(f"{scenario_plan.comparison_question} {scenario_plan.comparison.title}")
    overlap = {token for token in scenario_tokens & workspace_tokens if token not in {"scenario", "comparison"}}
    return bool(overlap)


def _scenario_namespace_slug(scenario_plan: ScenarioPlan) -> str:
    for candidate in [
        _neutral_comparison_title(
            comparison_question=scenario_plan.comparison_question,
            suggested_title=scenario_plan.comparison.title,
        ),
        scenario_plan.comparison_question,
    ]:
        stem = _comparison_stem(candidate)
        slug = slugify(stem)[:48]
        if slug:
            return slug
    return ""


def _comparison_stem(value: str) -> str:
    text = " ".join((value or "").strip().split())
    if not text:
        return ""
    if ":" in text:
        text = text.split(":", 1)[0].strip()
    lowered = text.lower()
    for suffix in ["scenario comparison", "comparative analysis", "comparison"]:
        if lowered.endswith(suffix):
            text = text[: -len(suffix)].strip(" :-")
            lowered = text.lower()
    return text


def _neutral_comparison_title(*, comparison_question: str, suggested_title: str) -> str:
    cleaned = " ".join((suggested_title or "").strip().split())
    if cleaned and not _looks_outcome_biased(cleaned):
        return cleaned
    topic = _question_topic_title(comparison_question)
    if topic:
        return f"{topic} Comparison"
    return cleaned or "Scenario Comparison"


def _looks_outcome_biased(title: str) -> bool:
    lowered = title.lower()
    return any(
        phrase in lowered
        for phrase in [
            "best fit",
            "is best",
            "recommended",
            "recommendation",
            "winner",
            "should choose",
            "should pursue",
            "should use",
        ]
    )


def _question_topic_title(question: str) -> str:
    lowered = " ".join((question or "").strip().lower().split())
    if not lowered:
        return ""
    if "launch" in lowered and any(term in lowered for term in ["strategy", "approach", "rollout"]):
        return "Launch Strategy"
    milestone_match = _milestone_phrase(lowered)
    if milestone_match:
        return f"{milestone_match} Scenario"
    if "product direction" in lowered:
        return "Product Direction"
    if "scope" in lowered and "milestone" in lowered:
        return "Milestone Scope"
    return ""


def _milestone_phrase(text: str) -> str:
    words = text.split()
    for index, word in enumerate(words[:-1]):
        if word == "milestone" and words[index + 1].isdigit():
            return f"Milestone {words[index + 1]}"
    return ""


def _clean_branch_title(branch: ScenarioBranchPlan, *, index: int) -> str:
    raw_title = " ".join((branch.title or "").strip().split())
    fallback = _humanize_label(branch.label) or f"Scenario {index}"
    if not raw_title:
        return fallback
    if len(raw_title.split()) > 6 or raw_title.endswith(".") or "," in raw_title or ":" in raw_title:
        return fallback
    return raw_title


def _clean_branch_card(branch: ScenarioBranchPlan) -> str:
    raw_card = _summarize_text(branch.card, fallback="")
    if raw_card:
        return raw_card
    if branch.title:
        title_summary = _summarize_text(branch.title, fallback="")
        if title_summary and title_summary != f"{branch.title}.":
            return title_summary
    for values in [branch.first_order_effects, branch.changed_assumptions, branch.risks]:
        first = _first_line(values)
        if first:
            return _summarize_text(first, fallback="")
    return "Scenario branch ready to compare and refine."


def _scenario_kind_for_record_type(record_type: str) -> str | None:
    if record_type == "scenario_comparison":
        return "comparison"
    return None


def _humanize_label(value: str) -> str:
    words = [part for part in str(value or "").replace("_", "-").split("-") if part]
    if not words:
        return ""
    upper_words = {"mvp", "ui", "ux", "api", "llm"}
    return " ".join(word.upper() if word.lower() in upper_words else word.capitalize() for word in words)


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


def _serialize_selected_record_payload(
    selected_record: CandidateMemory | None,
    *,
    comes_from: list[str] | None = None,
) -> dict[str, Any] | None:
    if selected_record is None:
        return None
    excerpt = selected_record.body.strip()
    if len(excerpt) > 1200:
        excerpt = f"{excerpt[:1197].rstrip()}..."
    lineage = [str(value).strip() for value in comes_from or [] if str(value).strip()]
    scenario_metadata = parse_artifact_scenario_metadata(
        selected_record.body,
        record_id=selected_record.id,
        record_type=selected_record.type,
        comes_from=lineage,
    ) or {}
    scenario_kind = scenario_metadata.get("scenario_kind") or _scenario_kind_for_record_type(selected_record.type)
    payload = {
        "id": selected_record.id,
        "title": selected_record.title,
        "type": selected_record.type,
        "scenario_kind": scenario_kind,
        "card": selected_record.card,
        "source": selected_record.source,
        "trust": selected_record.trust,
        "path": selected_record.path,
        "reason": selected_record.reason,
        "body_excerpt": excerpt,
        "comes_from": lineage,
        "scenario": scenario_metadata or None,
    }
    payload.update(scenario_metadata)
    return payload


def _candidate_source_priority(source: str) -> int:
    return {
        "concept": 3,
        "memory": 2,
        "artifact": 2,
        "vault_note": 1,
    }.get(source, 0)


def _cleanup_paths(paths: list[Path]) -> None:
    for path in reversed(paths):
        try:
            path.unlink()
        except FileNotFoundError:
            continue
