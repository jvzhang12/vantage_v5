from __future__ import annotations

from pathlib import Path

from vantage_v5.services.context_engine import ChatTurnRequestContext
from vantage_v5.services.context_engine import PreparedTurnContext
from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.services.protocol_engine import ProtocolEngine
from vantage_v5.services.protocols import build_protocol_write_from_interpretation
from vantage_v5.services.protocols import ProtocolInterpretation
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.markdown_store import MarkdownRecord
from vantage_v5.storage.workspaces import WorkspaceDocument


class _ExperimentManager:
    def get_active_session(self) -> None:
        return None


def _request() -> ChatTurnRequestContext:
    return ChatTurnRequestContext(
        durable_scope={"experiment_manager": _ExperimentManager()},
        message="Compare launch paths.",
        history=[],
        workspace_id="workspace",
        workspace_scope="excluded",
        workspace_content=None,
        whiteboard_mode="auto",
        pinned_context_id=None,
        memory_intent="auto",
        pending_workspace_update=None,
    )


def _context(tmp_path: Path) -> PreparedTurnContext:
    workspace = WorkspaceDocument(
        workspace_id="workspace",
        title="Workspace",
        content="",
        path=tmp_path / "workspace.md",
        scenario_metadata=None,
    )
    return PreparedTurnContext(
        session=None,
        runtime={},
        resolved_workspace_id="workspace",
        normalized_workspace_scope="excluded",
        workspace_loaded=True,
        workspace=workspace,
        transient_workspace=False,
        pinned_context=None,
        pending_workspace_update=None,
        whiteboard_entry_mode=None,
        continuity_context={},
    )


def test_protocol_engine_resolves_supported_apply_protocol_actions(tmp_path: Path) -> None:
    resolved = ProtocolEngine().resolve_for_turn(
        navigation=NavigationDecision(
            mode="scenario_lab",
            confidence=0.9,
            reason="Use Scenario Lab.",
            control_panel={
                "actions": [
                    {"type": "apply_protocol", "protocol_kind": "scenario_lab", "reason": "Use scenario reasoning."},
                    {"type": "apply_protocol", "kind": "email", "reason": "Use email style."},
                    {"type": "respond", "reason": "Answer after protocols."},
                ]
            },
        ),
        request=_request(),
        context=_context(tmp_path),
    )

    assert resolved.applied_protocol_kinds == ["scenario_lab", "email"]
    assert [action.reason for action in resolved.actions] == ["Use scenario reasoning.", "Use email style."]
    assert resolved.warnings == ()


def test_protocol_engine_dedupes_and_warns_for_unsupported_protocols(tmp_path: Path) -> None:
    resolved = ProtocolEngine().resolve_for_turn(
        navigation=NavigationDecision(
            mode="chat",
            confidence=0.9,
            reason="Apply protocol.",
            control_panel={
                "actions": [
                    {"type": "apply_protocol", "protocol_kind": "scenario_lab"},
                    {"type": "apply_protocol", "protocol_kind": "unknown"},
                    {"type": "apply_protocol", "protocol_kind": "scenario_lab"},
                ]
            },
        ),
        request=_request(),
        context=_context(tmp_path),
    )

    assert resolved.applied_protocol_kinds == ["scenario_lab"]
    assert resolved.warnings == ("Ignored unsupported protocol action at index 1.",)


def test_protocol_engine_ignores_missing_control_panel(tmp_path: Path) -> None:
    resolved = ProtocolEngine().resolve_for_turn(
        navigation=NavigationDecision(mode="chat", confidence=0.7, reason="No protocols."),
        request=_request(),
        context=_context(tmp_path),
    )

    assert resolved.applied_protocol_kinds == []
    assert resolved.to_dict() == {"applied_protocol_kinds": [], "actions": [], "warnings": []}


def test_protocol_engine_loads_email_protocol_from_task_surface(tmp_path: Path) -> None:
    request = _request()
    request.message = "Draft an email to Priya thanking her for the feedback."

    resolved = ProtocolEngine().resolve_for_turn(
        navigation=NavigationDecision(mode="chat", confidence=0.7, reason="No explicit protocol action."),
        request=request,
        context=_context(tmp_path),
    )

    assert resolved.applied_protocol_kinds == ["email"]
    assert resolved.actions[0].source == "task_surface"


def test_protocol_engine_loads_scenario_protocol_for_explicit_scenario_lab(tmp_path: Path) -> None:
    resolved = ProtocolEngine().resolve_for_turn(
        navigation=NavigationDecision(mode="scenario_lab", confidence=0.9, reason="Explicit Scenario Lab request."),
        request=_request(),
        context=_context(tmp_path),
    )

    assert resolved.applied_protocol_kinds == ["scenario_lab"]
    assert resolved.actions[0].source == "task_surface"


def test_protocol_engine_builds_guidance_from_persisted_protocol_override(tmp_path: Path) -> None:
    protocol_record = MarkdownRecord(
        id="scenario-lab-protocol",
        title="Custom Scenario Protocol",
        type="protocol",
        card="Use a custom scenario method.",
        body="Custom first principles body.",
        status="active",
        links_to=[],
        comes_from=[],
        path=tmp_path / "scenario-lab-protocol.md",
        source_value="concept",
        trust_value="high",
        metadata={
            "protocol_kind": "scenario_lab",
            "variables": {"default_surface": "premium_scenario_lab"},
            "applies_to": ["scenario lab"],
            "override_of_builtin": True,
        },
    )

    guidance = ProtocolEngine().build_guidance(
        protocol_kinds=["scenario_lab", "scenario_lab"],
        concept_records=[protocol_record],
    )

    assert guidance.applied_protocol_kinds == ["scenario_lab"]
    assert guidance.warnings == ()
    assert len(guidance.candidates) == 1
    candidate = guidance.candidates[0]
    assert candidate.id == "scenario-lab-protocol"
    assert candidate.title == "Custom Scenario Protocol"
    assert candidate.protocol == {
        "protocol_kind": "scenario_lab",
        "variables": {"default_surface": "premium_scenario_lab"},
        "applies_to": ["scenario lab"],
        "modifiable": True,
        "is_builtin": False,
        "is_canonical": False,
        "overrides_builtin": True,
        "overrides_canonical": False,
    }


def test_protocol_engine_builds_guidance_from_builtin_when_no_override(tmp_path: Path) -> None:
    guidance = ProtocolEngine().build_guidance(
        protocol_kinds=["unknown", "scenario_lab"],
        concept_records=[],
    )

    assert guidance.applied_protocol_kinds == ["scenario_lab"]
    assert guidance.warnings == ("Ignored unsupported protocol kind: unknown",)
    assert len(guidance.candidates) == 1
    candidate = guidance.candidates[0]
    assert candidate.id == "scenario-lab-protocol"
    assert candidate.protocol["protocol_kind"] == "scenario_lab"
    assert candidate.protocol["is_builtin"] is True
    assert "counterfactual reasoning" in candidate.body
    assert guidance.to_dict()["candidate_count"] == 1


def test_protocol_engine_lists_persisted_protocols_and_missing_builtins(tmp_path: Path) -> None:
    protocol_record = MarkdownRecord(
        id="email-drafting-protocol",
        title="Email Drafting Protocol",
        type="protocol",
        card="Email rules.",
        body="Body.",
        status="active",
        links_to=[],
        comes_from=[],
        path=tmp_path / "email-drafting-protocol.md",
        source_value="concept",
        trust_value="high",
        metadata={"protocol_kind": "email"},
    )

    catalog = ProtocolEngine().list_catalog(
        concept_records=[protocol_record],
        include_builtins=True,
    )

    assert [entry.record.id if entry.record else entry.built_in_kind for entry in catalog.entries] == [
        "email-drafting-protocol",
        "scenario_lab",
    ]


def test_protocol_engine_lookup_prefers_persisted_protocol_over_builtin(tmp_path: Path) -> None:
    protocol_record = MarkdownRecord(
        id="scenario-lab-protocol",
        title="Custom Scenario Protocol",
        type="protocol",
        card="Custom scenario rules.",
        body="Body.",
        status="active",
        links_to=[],
        comes_from=[],
        path=tmp_path / "scenario-lab-protocol.md",
        source_value="concept",
        trust_value="high",
        metadata={"protocol_kind": "scenario_lab", "override_of_builtin": True},
    )

    entry = ProtocolEngine().lookup_catalog_entry(
        concept_records=[protocol_record],
        protocol_kind_or_id="scenario_lab",
    )

    assert entry is not None
    assert entry.record == protocol_record
    assert entry.built_in_kind is None


def test_protocol_engine_lookup_can_return_builtin_protocol() -> None:
    entry = ProtocolEngine().lookup_catalog_entry(
        concept_records=[],
        protocol_kind_or_id="scenario-lab-protocol",
    )

    assert entry is not None
    assert entry.record is None
    assert entry.built_in_kind == "scenario_lab"


def test_protocol_engine_update_from_api_persists_builtin_override(tmp_path: Path) -> None:
    concept_store = ConceptStore(tmp_path / "concepts")

    protocol = ProtocolEngine().update_from_api(
        protocol_kind="scenario_lab",
        concept_records=[],
        concept_store=concept_store,
        title="Scenario Lab Protocol",
        card="Use clean tradeoff reasoning.",
        body="Compare branches from first principles.",
        variables={"default_surface": "scenario_lab"},
        applies_to=["scenario lab"],
    )

    assert protocol.id == "scenario-lab-protocol"
    assert protocol.metadata["protocol_kind"] == "scenario_lab"
    assert protocol.metadata["override_of_builtin"] is True
    assert protocol.metadata["variables"]["default_surface"] == "scenario_lab"
    assert (tmp_path / "concepts" / "scenario-lab-protocol.md").exists()


def test_protocol_engine_interprets_and_applies_protocol_update(tmp_path: Path) -> None:
    concept_store = ConceptStore(tmp_path / "concepts")
    engine = ProtocolEngine()

    class _Interpreter:
        def interpret(self, **kwargs):
            return ProtocolInterpretation(
                protocol_write=build_protocol_write_from_interpretation(
                    protocol_kind="email",
                    variables={"signature": "Jordan Zhang"},
                    applies_to=["email"],
                    source_instruction="Always sign emails with Jordan Zhang.",
                    existing_protocols=kwargs["existing_protocols"],
                ),
                recall_protocol_kinds=["email"],
                rationale="The user updated a reusable email protocol.",
            )

    engine.protocol_interpreter = _Interpreter()

    result = engine.interpret_and_apply(
        message="Always sign my emails with Jordan Zhang.",
        history=[],
        concept_records=[],
        concept_store=concept_store,
    )

    assert result.protocol_action is not None
    assert result.protocol_action.action == "upsert_protocol"
    assert result.protocol_action.record_id == "email-drafting-protocol"
    assert result.protocol_record is not None
    assert result.protocol_record.metadata["variables"]["signature"] == "Jordan Zhang"
    assert result.recall_protocol_kinds == ("email",)
    assert [record.id for record in result.concept_records] == ["email-drafting-protocol"]
    assert (tmp_path / "concepts" / "email-drafting-protocol.md").exists()


def test_protocol_engine_suppresses_one_off_draft_protocol_update(tmp_path: Path) -> None:
    concept_store = ConceptStore(tmp_path / "concepts")
    engine = ProtocolEngine()

    class _Interpreter:
        def interpret(self, **kwargs):
            return ProtocolInterpretation(
                protocol_write=build_protocol_write_from_interpretation(
                    protocol_kind="email",
                    variables={"tone": "warm"},
                    applies_to=["email"],
                    source_instruction=kwargs["message"],
                    existing_protocols=kwargs["existing_protocols"],
                ),
                recall_protocol_kinds=["email"],
                rationale="The protocol should guide this email draft.",
            )

    engine.protocol_interpreter = _Interpreter()

    result = engine.interpret_and_apply(
        message="Draft an email inviting a trusted beta tester next week.",
        history=[],
        concept_records=[],
        concept_store=concept_store,
    )

    assert result.protocol_action is None
    assert result.protocol_record is None
    assert result.recall_protocol_kinds == ("email",)
    assert result.concept_records == ()
    assert not (tmp_path / "concepts" / "email-drafting-protocol.md").exists()


def test_protocol_engine_interpret_without_update_preserves_concepts(tmp_path: Path) -> None:
    existing = MarkdownRecord(
        id="counting-concept",
        title="Counting",
        type="concept",
        card="Counting concept.",
        body="Counting body.",
        status="active",
        links_to=[],
        comes_from=[],
        path=tmp_path / "counting-concept.md",
        source_value="concept",
        trust_value="high",
    )
    engine = ProtocolEngine()

    class _Interpreter:
        def interpret(self, **kwargs):
            return ProtocolInterpretation(
                protocol_write=None,
                recall_protocol_kinds=["research_paper"],
                rationale="Recall the research paper protocol, but do not update it.",
            )

    engine.protocol_interpreter = _Interpreter()

    result = engine.interpret_and_apply(
        message="Help polish the abstract.",
        history=[],
        concept_records=[existing],
        concept_store=ConceptStore(tmp_path / "concepts"),
    )

    assert result.protocol_action is None
    assert result.protocol_record is None
    assert result.recall_protocol_kinds == ("research_paper",)
    assert result.concept_records == (existing,)
    assert result.rationale == "Recall the research paper protocol, but do not update it."
