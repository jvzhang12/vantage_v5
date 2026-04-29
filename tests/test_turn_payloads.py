from __future__ import annotations

from pathlib import Path
from typing import Any

from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.turn_staging import StageAuditResult
from vantage_v5.services.turn_staging import StageProgressEvent
from vantage_v5.services.turn_staging import TurnStage
from vantage_v5.services.turn_payloads import assemble_local_turn_payload
from vantage_v5.services.turn_payloads import assemble_scenario_lab_fallback_payload
from vantage_v5.services.turn_payloads import assemble_service_turn_payload
from vantage_v5.services.turn_payloads import assemble_scenario_lab_turn_body
from vantage_v5.services.turn_payloads import assemble_turn_interpretation_payload
from vantage_v5.services.turn_payloads import assemble_workspace_payload_for_turn
from vantage_v5.services.turn_payloads import assemble_chat_turn_body
from vantage_v5.services.turn_payloads import build_local_turn_parts
from vantage_v5.services.turn_payloads import ChatTurnBodyParts
from vantage_v5.services.turn_payloads import finalize_turn_payload
from vantage_v5.services.turn_payloads import LocalTurnBodyParts
from vantage_v5.services.turn_payloads import LocalTurnContext
from vantage_v5.services.turn_payloads import ScenarioLabTurnBodyParts
from vantage_v5.services.turn_payloads import ScenarioLabFallbackParts
from vantage_v5.services.turn_payloads import ServiceTurnPayloadParts
from vantage_v5.services.turn_payloads import TurnInterpretationParts
from vantage_v5.services.turn_payloads import TurnResultParts
from vantage_v5.storage.workspaces import WorkspaceDocument


def _workspace(tmp_path: Path, content: str) -> WorkspaceDocument:
    return WorkspaceDocument(
        workspace_id="draft",
        title="Draft",
        content=content,
        path=tmp_path / "draft.md",
        scenario_metadata=None,
    )


def _answer_basis_for(
    *,
    working_memory: list[dict[str, Any]] | None = None,
    context_sources: list[str] | None = None,
    learned: list[dict[str, Any]] | None = None,
    created_record: dict[str, Any] | None = None,
    recall_count: int = 0,
) -> dict[str, Any]:
    payload = finalize_turn_payload(
        {
            "working_memory": working_memory or [],
            "learned": learned or [],
            "created_record": created_record,
            "response_mode": {
                "kind": "grounded" if context_sources else "best_guess",
                "grounding_mode": "mixed_context" if context_sources and len(context_sources) > 1 else "ungrounded",
                "context_sources": context_sources or [],
                "grounding_sources": context_sources or [],
                "recall_count": recall_count,
            },
        },
        pinned_context_id=None,
        pinned_context=None,
    )
    return payload["answer_basis"]


def _memory_item(record_id: str = "memory-1") -> dict[str, Any]:
    return {
        "id": record_id,
        "title": "Useful Memory",
        "type": "note",
        "kind": "saved_note",
        "memory_role": "saved_context",
        "source_tier": "saved",
        "source": "memory",
    }


def _protocol_item(record_id: str = "protocol-1") -> dict[str, Any]:
    return {
        "id": record_id,
        "title": "Email Protocol",
        "type": "protocol",
        "kind": "protocol",
        "memory_role": "protocol",
        "source_tier": "instruction",
        "source": "concept",
        "protocol": {"protocol_kind": "email"},
    }


def _assert_review_first_write_review(record: dict[str, Any]) -> None:
    review = record["write_review"]
    assert review["write_reason"]
    assert review["scope"] == record.get("scope", "durable")
    assert review["durability"] == record.get("durability", "durable")
    assert review["record"]["id"] == record["id"]
    assert review["record"]["source"] == record["source"]
    assert {action["kind"] for action in review["allowed_actions"]} == {
        "open_in_whiteboard",
        "revise_in_whiteboard",
        "pin_for_next_turn",
    }
    assert review["direct_mutation_supported"] is False
    assert review["mutation_supported"] is False
    assert review["unsupported_actions"] == [
        {"kind": "direct_mutation", "label": "Direct mutation is not supported"}
    ]


def _budget_row(payload: dict[str, Any], key: str) -> dict[str, Any]:
    rows = payload["context_budget"]["rows"]
    return next(row for row in rows if row["key"] == key)


def test_answer_basis_maps_intuitive_without_context() -> None:
    basis = _answer_basis_for(recall_count=4)

    assert basis["kind"] == "intuitive"
    assert basis["label"] == "Intuitive Answer"
    assert basis["has_factual_grounding"] is False
    assert basis["sources"] == []
    assert basis["counts"] == {
        "memory": 0,
        "protocol": 0,
        "whiteboard": 0,
        "conversation": 0,
        "recalled_items": 0,
    }


def test_answer_basis_maps_memory_only_from_actual_recall_items() -> None:
    basis = _answer_basis_for(
        working_memory=[_memory_item()],
        context_sources=["recall"],
        recall_count=0,
    )

    assert basis["kind"] == "memory_backed"
    assert basis["label"] == "Memory-Backed"
    assert basis["has_factual_grounding"] is True
    assert basis["sources"] == ["memory"]
    assert basis["evidence_sources"] == ["memory"]
    assert basis["guidance_sources"] == []
    assert basis["counts"]["memory"] == 1
    assert basis["counts"]["recalled_items"] == 1


def test_answer_basis_maps_protocol_only_as_guidance() -> None:
    basis = _answer_basis_for(
        working_memory=[_protocol_item()],
        context_sources=["recall"],
    )

    assert basis["kind"] == "protocol_guided"
    assert basis["label"] == "Protocol-Guided"
    assert basis["has_factual_grounding"] is False
    assert basis["sources"] == ["protocol"]
    assert basis["evidence_sources"] == []
    assert basis["guidance_sources"] == ["protocol"]
    assert basis["counts"]["protocol"] == 1


def test_answer_basis_maps_whiteboard_only_as_grounded() -> None:
    basis = _answer_basis_for(context_sources=["whiteboard"])

    assert basis["kind"] == "whiteboard_grounded"
    assert basis["label"] == "Whiteboard-Grounded"
    assert basis["has_factual_grounding"] is True
    assert basis["sources"] == ["whiteboard"]
    assert basis["evidence_sources"] == ["whiteboard"]
    assert basis["counts"]["whiteboard"] == 1


def test_answer_basis_maps_pending_whiteboard_only_as_grounded() -> None:
    basis = _answer_basis_for(context_sources=["pending_whiteboard"])

    assert basis["kind"] == "whiteboard_grounded"
    assert basis["label"] == "Whiteboard-Grounded"
    assert basis["has_factual_grounding"] is True
    assert basis["sources"] == ["pending_whiteboard"]
    assert basis["evidence_sources"] == ["pending_whiteboard"]
    assert basis["counts"]["whiteboard"] == 1


def test_answer_basis_maps_recent_chat_only_with_compatibility_label() -> None:
    basis = _answer_basis_for(context_sources=["recent_chat"])

    assert basis["kind"] == "recent_chat"
    assert basis["label"] == "Recent Chat"
    assert basis["has_factual_grounding"] is True
    assert basis["sources"] == ["recent_chat"]
    assert basis["evidence_sources"] == ["recent_chat"]
    assert basis["counts"]["conversation"] == 1


def test_answer_basis_maps_protocol_plus_memory_as_mixed_context() -> None:
    basis = _answer_basis_for(
        working_memory=[_protocol_item(), _memory_item()],
        context_sources=["recall"],
    )

    assert basis["kind"] == "mixed_context"
    assert basis["label"] == "Mixed Context"
    assert basis["has_factual_grounding"] is True
    assert basis["sources"] == ["memory", "protocol"]
    assert basis["evidence_sources"] == ["memory"]
    assert basis["guidance_sources"] == ["protocol"]
    assert basis["counts"]["memory"] == 1
    assert basis["counts"]["protocol"] == 1


def test_answer_basis_maps_protocol_plus_whiteboard_as_mixed_context() -> None:
    basis = _answer_basis_for(
        working_memory=[_protocol_item()],
        context_sources=["recall", "whiteboard"],
    )

    assert basis["kind"] == "mixed_context"
    assert basis["label"] == "Mixed Context"
    assert basis["has_factual_grounding"] is True
    assert basis["sources"] == ["protocol", "whiteboard"]
    assert basis["evidence_sources"] == ["whiteboard"]
    assert basis["guidance_sources"] == ["protocol"]
    assert basis["counts"]["whiteboard"] == 1


def test_answer_basis_ignores_current_turn_created_protocol() -> None:
    created_protocol = {
        "id": "email-drafting-protocol",
        "title": "Email Protocol",
        "type": "protocol",
        "source": "concept",
    }

    basis = _answer_basis_for(
        working_memory=[_protocol_item("email-drafting-protocol")],
        context_sources=["recall"],
        learned=[created_protocol],
        created_record=created_protocol,
    )

    assert basis["kind"] == "intuitive"
    assert basis["label"] == "Intuitive Answer"
    assert basis["has_factual_grounding"] is False
    assert basis["sources"] == []
    assert basis["guidance_sources"] == []
    assert basis["counts"]["protocol"] == 0
    assert basis["counts"]["recalled_items"] == 0


def test_context_budget_summarizes_turn_scope_without_token_counts() -> None:
    payload = finalize_turn_payload(
        {
            "recall": [
                _memory_item("memory-1"),
                _protocol_item("protocol-1"),
                {"id": "trace-1", "title": "Trace", "source": "memory_trace", "type": "memory_trace"},
            ],
            "response_mode": {
                "kind": "grounded",
                "grounding_mode": "mixed_context",
                "context_sources": ["recall", "whiteboard", "recent_chat", "pending_whiteboard"],
                "grounding_sources": ["recall", "whiteboard", "recent_chat", "pending_whiteboard"],
                "recall_count": 3,
            },
            "workspace": {"context_scope": "visible"},
            "turn_interpretation": {
                "preserve_pinned_context": True,
                "pinned_context_reason": "The selected comparison remains the anchor.",
            },
        },
        pinned_context_id="comparison-1",
        pinned_context={"id": "comparison-1", "title": "Comparison", "source": "artifact"},
    )

    budget = payload["context_budget"]
    assert budget["label"] == "Context Budget"
    assert "Context budget:" in budget["summary"]
    assert "token" not in budget["summary"].lower()
    assert budget["counts"] == {
        "recall": 3,
        "memory": 2,
        "protocol": 1,
        "whiteboard": 1,
        "recent_chat": 1,
        "pending_whiteboard": 1,
        "pinned_context": 1,
        "memory_trace": 1,
    }
    assert _budget_row(payload, "user_request")["status"] == "included"
    assert _budget_row(payload, "recall")["count"] == 3
    assert _budget_row(payload, "protocol")["count"] == 1
    assert _budget_row(payload, "whiteboard")["scope"] == "Visible"
    assert _budget_row(payload, "recent_chat")["status"] == "included"
    assert _budget_row(payload, "pending_whiteboard")["status"] == "included"
    assert _budget_row(payload, "pinned_context")["detail"] == "The selected comparison remains the anchor."
    assert _budget_row(payload, "memory_trace")["count"] == 1


def test_assemble_turn_interpretation_payload_preserves_navigation_contract() -> None:
    navigation = NavigationDecision(
        mode="chat",
        confidence=0.87,
        reason="The user wants the current draft refined.",
        whiteboard_mode="auto",
        preserve_pinned_context=None,
        preserve_selected_record=True,
        selected_record_reason="The selected artifact remains the anchor.",
        control_panel={"actions": [{"type": "draft_whiteboard"}]},
    )

    payload = assemble_turn_interpretation_payload(
        TurnInterpretationParts(
            navigation=navigation,
            requested_whiteboard_mode="auto",
            resolved_whiteboard_mode="draft",
            whiteboard_entry_mode="continued_current",
            explicit_whiteboard_draft_request=True,
        )
    )

    assert payload == {
        "mode": "chat",
        "confidence": 0.87,
        "reason": "The user wants the current draft refined.",
        "requested_whiteboard_mode": "auto",
        "resolved_whiteboard_mode": "draft",
        "whiteboard_mode_source": "request",
        "whiteboard_entry_mode": "continued_current",
        "preserve_pinned_context": True,
        "pinned_context_reason": "The selected artifact remains the anchor.",
        "preserve_selected_record": True,
        "selected_record_reason": "The selected artifact remains the anchor.",
        "control_panel": {"actions": [{"type": "draft_whiteboard"}]},
    }


def test_assemble_turn_interpretation_payload_hides_whiteboard_resolution_for_scenario_lab() -> None:
    navigation = NavigationDecision(
        mode="scenario_lab",
        confidence=0.91,
        reason="Compare branches.",
        whiteboard_mode="draft",
        control_panel=None,
    )

    payload = assemble_turn_interpretation_payload(
        TurnInterpretationParts(
            navigation=navigation,
            requested_whiteboard_mode="draft",
            resolved_whiteboard_mode="draft",
            whiteboard_entry_mode="started_fresh",
            explicit_whiteboard_draft_request=True,
        )
    )

    assert payload["resolved_whiteboard_mode"] is None
    assert payload["whiteboard_mode_source"] is None
    assert payload["control_panel"] == {}


def test_assemble_workspace_payload_for_turn_merges_visibility_and_scenario_metadata(tmp_path: Path) -> None:
    workspace = WorkspaceDocument(
        workspace_id="scenario",
        title="Scenario",
        content="# Scenario\n\nVisible branch.",
        path=tmp_path / "scenario.md",
        scenario_metadata={
            "scenario_kind": "comparison_branch",
            "empty": "",
            "branch": {"label": "Balanced", "notes": ""},
        },
    )

    payload = assemble_workspace_payload_for_turn(
        {"workspace_id": "legacy", "title": "Legacy", "content": None, "extra": "kept"},
        workspace=workspace,
        scope="experiment",
        context_scope="visible",
        transient_workspace=True,
    )

    assert payload["workspace_id"] == "scenario"
    assert payload["title"] == "Scenario"
    assert payload["content"] == "# Scenario\n\nVisible branch."
    assert payload["scope"] == "experiment"
    assert payload["context_scope"] == "visible"
    assert payload["extra"] == "kept"
    assert payload["scenario_kind"] == "comparison_branch"
    assert payload["scenario"] == {"scenario_kind": "comparison_branch", "branch": {"label": "Balanced"}}


def test_assemble_workspace_payload_for_turn_hides_durable_content_when_not_transient(tmp_path: Path) -> None:
    payload = assemble_workspace_payload_for_turn(
        None,
        workspace=_workspace(tmp_path, "# Durable\n\nHidden from turn payload."),
        scope="durable",
        context_scope="excluded",
        transient_workspace=False,
    )

    assert payload["content"] is None
    assert payload["context_scope"] == "excluded"


def test_assemble_local_turn_payload_preserves_local_action_contract(tmp_path: Path) -> None:
    turn_interpretation = TurnInterpretationParts(
        navigation=NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="The user explicitly asked to save the visible whiteboard.",
        ),
        requested_whiteboard_mode="auto",
        resolved_whiteboard_mode="chat",
        whiteboard_entry_mode="continued_current",
        explicit_whiteboard_draft_request=False,
    )
    payload = assemble_local_turn_payload(
        build_local_turn_parts(
            LocalTurnContext(
                user_message="save this",
                history=[{"user_message": "draft this", "assistant_message": "Sure."}],
                workspace=_workspace(tmp_path, "# Draft\n\nVisible content."),
                workspace_scope="visible",
                runtime_scope="durable",
                transient_workspace=True,
                semantic_frame={"task_type": "artifact_save"},
                semantic_policy={"action_type": "artifact_save", "reason": "The whiteboard is visible."},
                pinned_context_id="saved-record",
                pinned_context={"id": "saved-record", "title": "Saved Record", "source": "artifact"},
                experiment={"active": False, "session_id": None},
            ),
            turn_body=LocalTurnBodyParts(
                assistant_message="I saved Draft as a whiteboard snapshot.",
                mode="local_action",
                graph_action={"type": "save_workspace_iteration_artifact", "record_id": "artifact-1"},
                created_record={"id": "artifact-1", "title": "Draft", "source": "artifact"},
            ),
            turn_interpretation=turn_interpretation,
        )
    )

    assert payload["mode"] == "local_action"
    assert payload["workspace"]["context_scope"] == "visible"
    assert payload["response_mode"]["grounding_mode"] == "mixed_context"
    assert payload["response_mode"]["context_sources"] == ["whiteboard", "recent_chat"]
    assert payload["graph_action"]["concept_id"] == "artifact-1"
    assert payload["created_record"]["id"] == "artifact-1"
    assert payload["learned"] == [payload["created_record"]]
    assert payload["pinned_context_id"] == "saved-record"
    assert payload["selected_record_id"] == "saved-record"
    assert payload["turn_interpretation"]["reason"] == "The user explicitly asked to save the visible whiteboard."
    assert payload["turn_interpretation"]["whiteboard_entry_mode"] == "continued_current"
    assert payload["system_state"]["workspace"]["has_visible_content"] is True
    assert payload["activity"]["mode"] == "local_action"


def test_assemble_local_turn_payload_keeps_hidden_workspace_content_out_of_scope(tmp_path: Path) -> None:
    payload = assemble_local_turn_payload(
        TurnResultParts(
            user_message="save this",
            history=[],
            workspace=_workspace(tmp_path, ""),
            workspace_scope="excluded",
            runtime_scope="durable",
            transient_workspace=False,
            semantic_frame={"task_type": "artifact_save"},
            semantic_policy={"action_type": "artifact_save", "should_clarify": True, "reason": "No visible target."},
            pinned_context_id=None,
            pinned_context=None,
            experiment={"active": False, "session_id": None},
            turn_body=LocalTurnBodyParts(
                assistant_message="What should I save?",
                mode="clarification",
            ),
        )
    )

    assert payload["mode"] == "clarification"
    assert payload["workspace"]["content"] is None
    assert payload["response_mode"]["kind"] == "best_guess"
    assert payload["response_mode"]["context_sources"] == []
    assert payload["system_state"]["workspace"]["has_visible_content"] is False
    assert payload["created_record"] is None


def test_assemble_scenario_lab_fallback_payload_preserves_failure_contract(tmp_path: Path) -> None:
    payload = assemble_scenario_lab_fallback_payload(
        ScenarioLabFallbackParts(
            turn_body=ChatTurnBodyParts(
                user_message="compare paths",
                assistant_message="I answered in chat after Scenario Lab failed.",
                workspace_id="draft",
                workspace_title="Draft",
                workspace_content=None,
                workspace_update=None,
                concept_cards=[],
                trace_notes=[],
                saved_notes=[],
                vault_notes=[],
                candidate_concepts=[],
                candidate_trace_notes=[],
                candidate_saved_notes=[],
                candidate_vault_notes=[],
                candidate_memory=[],
                working_memory=[],
                recall_details=[],
                learned=[],
                memory_trace_record=None,
                response_mode={"recall_count": 0},
                vetting={"selected_ids": []},
                mode="chat",
                meta_action=None,
                graph_action=None,
                created_record=None,
            ),
            navigation={"mode": "scenario_lab", "reason": "Compare branches."},
            comparison_question="Which launch path?",
            reason="Compare branches.",
            error_type="RuntimeError",
            error_message="boom",
            pinned_context_id="comparison",
            pinned_context={"id": "comparison", "title": "Comparison", "source": "artifact"},
            turn_interpretation=TurnInterpretationParts(
                navigation=NavigationDecision(
                    mode="scenario_lab",
                    confidence=0.91,
                    reason="Compare branches.",
                ),
                requested_whiteboard_mode="auto",
                resolved_whiteboard_mode="draft",
                whiteboard_entry_mode="started_fresh",
                explicit_whiteboard_draft_request=False,
            ),
            semantic_frame={"task_type": "scenario_compare"},
            semantic_policy={"action_type": "none"},
            workspace=_workspace(tmp_path, "# Draft\n\nVisible context."),
            runtime_scope="durable",
            workspace_scope="visible",
            transient_workspace=True,
            experiment={"active": False, "session_id": None},
        )
    )

    assert payload["mode"] == "chat"
    assert payload["scenario_lab"]["status"] == "failed"
    assert payload["scenario_lab"]["fallback_mode"] == "chat"
    assert payload["scenario_lab"]["chat_turn_mode"] == "chat"
    assert payload["scenario_lab_error"] == {"type": "RuntimeError", "message": "boom"}
    assert payload["turn_interpretation"]["mode"] == "scenario_lab"
    assert payload["turn_interpretation"]["resolved_whiteboard_mode"] is None
    assert payload["pinned_context_id"] == "comparison"
    assert payload["selected_record_id"] == "comparison"
    assert payload["workspace"]["context_scope"] == "visible"
    assert payload["activity"]["mode"] == "chat"


def test_assemble_service_turn_payload_preserves_successful_turn_contract(tmp_path: Path) -> None:
    payload = assemble_service_turn_payload(
        ServiceTurnPayloadParts(
            turn_body=ChatTurnBodyParts(
                user_message="draft this",
                assistant_message="I drafted this into the whiteboard.",
                workspace_id="draft",
                workspace_title="Draft",
                workspace_content=None,
                workspace_update={"status": "draft_ready", "summary": "Draft ready."},
                concept_cards=[],
                trace_notes=[],
                saved_notes=[],
                vault_notes=[],
                candidate_concepts=[],
                candidate_trace_notes=[],
                candidate_saved_notes=[],
                candidate_vault_notes=[],
                candidate_memory=[],
                working_memory=[],
                recall_details=[],
                learned=[],
                memory_trace_record=None,
                response_mode={"recall_count": 0},
                vetting={"selected_ids": []},
                mode="chat",
                meta_action=None,
                graph_action={"type": "save_workspace_iteration_artifact", "concept_id": "artifact-1"},
                created_record={"id": "artifact-1", "title": "Draft", "source": "artifact"},
            ),
            pinned_context_id="pinned",
            pinned_context={"id": "pinned", "title": "Pinned", "source": "artifact"},
            turn_interpretation=TurnInterpretationParts(
                navigation=NavigationDecision(
                    mode="chat",
                    confidence=0.86,
                    reason="Draft requested.",
                ),
                requested_whiteboard_mode="auto",
                resolved_whiteboard_mode="draft",
                whiteboard_entry_mode="continued_current",
                explicit_whiteboard_draft_request=True,
            ),
            semantic_frame={"task_type": "draft"},
            semantic_policy={"action_type": "none"},
            workspace=_workspace(tmp_path, "# Draft\n\nCurrent content."),
            runtime_scope="durable",
            workspace_scope="visible",
            transient_workspace=True,
            experiment={"active": False, "session_id": None},
        )
    )

    assert payload["turn_interpretation"]["reason"] == "Draft requested."
    assert payload["semantic_frame"]["task_type"] == "draft"
    assert payload["semantic_policy"]["action_type"] == "none"
    assert payload["graph_action"]["record_id"] == "artifact-1"
    assert payload["learned"] == [payload["created_record"]]
    assert payload["workspace"]["content"] == "# Draft\n\nCurrent content."
    assert payload["workspace"]["context_scope"] == "visible"
    assert payload["experiment"]["active"] is False
    assert payload["system_state"]["workspace"]["has_visible_content"] is True
    assert payload["activity"]["workspace_update_status"] == "draft_ready"


def test_assemble_service_turn_payload_preserves_staging_payloads(tmp_path: Path) -> None:
    payload = assemble_service_turn_payload(
        ServiceTurnPayloadParts(
            turn_body=ChatTurnBodyParts(
                user_message="draft this",
                assistant_message="I drafted this into the whiteboard.",
                workspace_id="draft",
                workspace_title="Draft",
                workspace_content=None,
                workspace_update={"status": "draft_ready"},
                concept_cards=[],
                trace_notes=[],
                saved_notes=[],
                vault_notes=[],
                candidate_concepts=[],
                candidate_trace_notes=[],
                candidate_saved_notes=[],
                candidate_vault_notes=[],
                candidate_memory=[],
                working_memory=[],
                recall_details=[],
                learned=[],
                memory_trace_record=None,
                response_mode={"recall_count": 0},
                vetting={"selected_ids": []},
                mode="chat",
                meta_action=None,
                graph_action=None,
                created_record=None,
                turn_stage=TurnStage(
                    stage_id="draft",
                    task_kind="whiteboard_draft",
                    contract={"workspace_update_type": "draft_whiteboard", "schema": {"hidden": True}},
                    max_attempts=0,
                    reason="Prepare a whiteboard draft.",
                ),
                stage_progress=StageProgressEvent(
                    event_id="draft",
                    status="retrying",
                    label="Repairing draft",
                ),
                stage_audit=StageAuditResult(
                    accepted=False,
                    status="retry",
                    issues=("Draft whiteboard update needs draft content.",),
                    retry_instruction="Return a draft_whiteboard workspace_update with title and content.",
                ),
            ),
            pinned_context_id=None,
            pinned_context=None,
            turn_interpretation=None,
            semantic_frame={"task_type": "draft"},
            semantic_policy={"action_type": "none"},
            workspace=_workspace(tmp_path, "# Draft\n\nCurrent content."),
            runtime_scope="durable",
            workspace_scope="visible",
            transient_workspace=True,
            experiment={"active": False, "session_id": None},
        )
    )

    assert {
        key: payload["turn_stage"][key]
        for key in ("stage_id", "task_kind", "contract", "max_attempts", "reason")
    } == {
        "stage_id": "draft",
        "task_kind": "whiteboard_draft",
        "contract": {"workspace_update_type": "draft_whiteboard"},
        "max_attempts": 1,
        "reason": "Prepare a whiteboard draft.",
    }
    assert payload["turn_stage"]["label"] == "Whiteboard draft"
    assert payload["stage_progress"]["id"] == "draft"
    assert payload["stage_progress"]["status"] == "retrying"
    assert payload["stage_progress"]["label"] == "Repairing draft"
    assert payload["stage_audit"]["retryable"] is True
    assert payload["stage_audit"]["retry_instruction"] == "Return a draft_whiteboard workspace_update with title and content."


def test_assemble_chat_turn_body_preserves_chat_payload_aliases() -> None:
    learned = [
        {
            "id": "artifact-1",
            "title": "Draft",
            "source": "artifact",
            "scope": "durable",
            "durability": "durable",
            "why_learned": "Saved as a whiteboard snapshot so the in-progress draft stays inspectable.",
            "correction_affordance": {"kind": "open_in_whiteboard", "label": "Open in whiteboard"},
        }
    ]
    payload = assemble_chat_turn_body(
        ChatTurnBodyParts(
            user_message="draft this",
            assistant_message="Here is a draft.",
            workspace_id="draft",
            workspace_title="Draft",
            workspace_content="# Draft",
            workspace_update={"status": "draft_ready"},
            concept_cards=[{"id": "concept-1"}],
            trace_notes=[{"id": "trace-1"}],
            saved_notes=[{"id": "memory-1", "source": "memory"}],
            vault_notes=[{"id": "vault-1", "source": "vault_note"}],
            candidate_concepts=[{"id": "candidate-concept"}],
            candidate_trace_notes=[{"id": "candidate-trace"}],
            candidate_saved_notes=[{"id": "candidate-memory"}],
            candidate_vault_notes=[{"id": "candidate-vault"}],
            candidate_memory=[{"id": "candidate-memory-result"}],
            working_memory=[{"id": "recalled-1"}],
            recall_details=[{"id": "recalled-1", "why_recalled": "Relevant."}],
            learned=learned,
            memory_trace_record={"id": "trace-record"},
            response_mode={"recall_count": 1},
            vetting={"selected_ids": ["recalled-1"]},
            mode="chat",
            meta_action={"action": "no_op"},
            graph_action={"type": "save_workspace_iteration_artifact"},
            created_record=None,
        )
    )

    assert payload["workspace"] == {"workspace_id": "draft", "title": "Draft", "content": "# Draft"}
    assert payload["memory"] == payload["selected_memory"]
    assert payload["memory"]["total"] == 2
    assert payload["candidate_memory"]["total"] == 2
    assert payload["turn_vault_notes"] == [{"id": "vault-1", "source": "vault_note"}]
    assert payload["candidate_memory_results"] == [{"id": "candidate-memory-result"}]
    assert payload["recall"] == payload["working_memory"]
    assert payload["recall_details"][0]["why_recalled"] == "Relevant."
    assert payload["learned"] == learned
    assert payload["created_record"] == learned[0]
    assert payload["created_record"]["why_learned"] == "Saved as a whiteboard snapshot so the in-progress draft stays inspectable."
    assert payload["created_record"]["correction_affordance"]["kind"] == "open_in_whiteboard"
    _assert_review_first_write_review(payload["created_record"])
    assert payload["answer_basis"]["kind"] == "memory_backed"
    assert payload["answer_basis"]["label"] == "Memory-Backed"


def test_assemble_scenario_lab_turn_body_preserves_scenario_payload_aliases() -> None:
    learned = [
        {
            "id": "comparison-1",
            "title": "Launch Comparison",
            "source": "artifact",
            "scope": "durable",
            "durability": "durable",
            "why_learned": "Saved as a Scenario Lab comparison hub so the branch comparison can be revisited.",
            "correction_affordance": {"kind": "open_in_whiteboard", "label": "Open in whiteboard"},
        }
    ]
    comparison_artifact = {
        "id": "comparison-1",
        "title": "Launch Comparison",
        "card": "Compare launch paths.",
        "recommendation": "Run the private beta.",
    }

    payload = assemble_scenario_lab_turn_body(
        ScenarioLabTurnBodyParts(
            user_message="compare launch paths",
            assistant_message="I compared three launch paths.",
            workspace_id="launch",
            workspace_title="Launch",
            workspace_content="# Launch",
            concept_cards=[{"id": "concept-1"}],
            saved_notes=[{"id": "artifact-context", "source": "artifact"}],
            vault_notes=[{"id": "vault-1", "source": "vault_note"}],
            candidate_concepts=[{"id": "candidate-concept"}],
            candidate_saved_notes=[{"id": "candidate-artifact"}],
            candidate_vault_notes=[{"id": "candidate-vault"}],
            candidate_memory=[{"id": "candidate-memory-result"}],
            working_memory=[{"id": "protocol-1"}],
            learned=learned,
            memory_trace_record={"id": "trace-record"},
            response_mode={"recall_count": 1},
            vetting={"selected_ids": ["protocol-1"]},
            navigator={"mode": "scenario_lab", "reason": "Compare branches."},
            comparison_question="Which launch path should we choose?",
            branches=[{"workspace_id": "launch--private-beta", "title": "Private Beta"}],
            comparison_artifact=comparison_artifact,
            created_record=None,
        )
    )

    assert payload["mode"] == "scenario_lab"
    assert payload["workspace"] == {"workspace_id": "launch", "title": "Launch", "content": "# Launch"}
    assert payload["memory"] == payload["selected_memory"]
    assert payload["memory"]["total"] == 2
    assert payload["candidate_memory"]["total"] == 2
    assert payload["recall"] == payload["working_memory"]
    assert payload["learned"] == learned
    assert payload["created_record"] == learned[0]
    assert payload["created_record"]["why_learned"] == "Saved as a Scenario Lab comparison hub so the branch comparison can be revisited."
    assert payload["created_record"]["correction_affordance"]["kind"] == "open_in_whiteboard"
    _assert_review_first_write_review(payload["created_record"])
    assert payload["meta_action"]["action"] == "no_op"
    assert payload["graph_action"] is None
    assert payload["scenario_lab"]["question"] == "Which launch path should we choose?"
    assert payload["scenario_lab"]["comparison_question"] == "Which launch path should we choose?"
    assert payload["scenario_lab"]["summary"] == "Compare launch paths."
    assert payload["scenario_lab"]["recommendation"] == "Run the private beta."
    assert payload["scenario_lab"]["branches"] == [{"workspace_id": "launch--private-beta", "title": "Private Beta"}]
    assert payload["scenario_lab"]["comparison_artifact"] == comparison_artifact
    assert payload["answer_basis"]["kind"] == "memory_backed"
    assert payload["answer_basis"]["label"] == "Memory-Backed"


def test_finalize_turn_payload_ignores_malformed_learned_and_created_record_aliases() -> None:
    payload = finalize_turn_payload(
        {
            "learned": [
                "artifact-1",
                None,
                {"id": "artifact-2", "title": "Draft", "source": "artifact"},
            ],
            "created_record": "artifact-1",
            "working_memory": [],
            "response_mode": {"recall_count": 0},
        },
        pinned_context_id=None,
        pinned_context=None,
    )

    assert payload["learned"] == [payload["created_record"]]
    assert payload["created_record"]["id"] == "artifact-2"
    _assert_review_first_write_review(payload["created_record"])


def test_finalize_turn_payload_does_not_alias_malformed_created_record() -> None:
    payload = finalize_turn_payload(
        {
            "learned": [],
            "created_record": ["artifact-1"],
            "working_memory": [],
            "response_mode": {"recall_count": 0},
        },
        pinned_context_id=None,
        pinned_context=None,
    )

    assert payload["learned"] == []
    assert payload["created_record"] is None
