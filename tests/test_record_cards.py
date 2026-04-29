from __future__ import annotations

from pathlib import Path

from vantage_v5.services.record_cards import memory_payload
from vantage_v5.services.record_cards import scenario_payload
from vantage_v5.services.record_cards import serialize_built_in_protocol_card
from vantage_v5.services.record_cards import serialize_concept_card
from vantage_v5.services.record_cards import serialize_saved_note_card
from vantage_v5.storage.artifacts import ArtifactStore
from vantage_v5.storage.concepts import ConceptStore
from vantage_v5.storage.memories import MemoryStore


def test_serialize_saved_note_card_preserves_artifact_lifecycle_and_scenario_fields(tmp_path: Path) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").create_artifact(
        title="Launch Path Comparison",
        card="Compare launch paths.",
        body="# Launch Path Comparison\n\n## Branches Compared\n- path-a\n- path-b\n\n## Recommendation\nChoose path A.",
        type="scenario_comparison",
        comes_from=["base-workspace", "path-a", "path-b"],
    )

    payload = serialize_saved_note_card(artifact, scope="durable")

    assert payload["id"] == artifact.id
    assert payload["source"] == "artifact"
    assert payload["kind"] == "saved_note"
    assert payload["artifact_origin"] == "scenario_lab"
    assert payload["artifact_lifecycle"] == "comparison_hub"
    assert payload["scenario_kind"] == "comparison"
    assert payload["scenario"]["branch_workspace_ids"] == ["path-a", "path-b"]
    assert payload["derived_from_id"] == "base-workspace"
    assert payload["lineage_kind"] == "provenance"


def test_serialize_concept_card_preserves_protocol_metadata(tmp_path: Path) -> None:
    protocol = ConceptStore(tmp_path / "concepts").upsert_protocol(
        protocol_id="email-drafting-protocol",
        title="Email Drafting Protocol",
        card="Use concise business email defaults.",
        body="## Procedure\n\nDraft clearly.",
        protocol_kind="email",
        variables={"signature": "Jordan Zhang"},
        applies_to=["email"],
        metadata={"override_of_builtin": True},
    )

    payload = serialize_concept_card(protocol, scope="experiment")

    assert payload["kind"] == "protocol"
    assert payload["memory_role"] == "protocol"
    assert payload["source_tier"] == "instruction"
    assert payload["scope"] == "experiment"
    assert payload["protocol"] == {
        "protocol_kind": "email",
        "variables": {"signature": "Jordan Zhang"},
        "applies_to": ["email"],
        "modifiable": True,
        "is_builtin": False,
        "is_canonical": False,
        "overrides_builtin": True,
        "overrides_canonical": False,
    }


def test_built_in_protocol_and_memory_payload_shapes_stay_compatible(tmp_path: Path) -> None:
    memory = MemoryStore(tmp_path / "memories").create_memory(
        title="Chat Preference",
        card="The user prefers chat-first UX.",
        body="Keep drafts in chat unless whiteboard is useful.",
    )
    memory_card = serialize_saved_note_card(memory, scope="experiment")
    protocol_card = serialize_built_in_protocol_card("scenario_lab")
    grouped = memory_payload([memory_card], [])

    assert memory_card["source_label"] == "Experiment memories"
    assert "artifact_lifecycle" not in memory_card
    assert protocol_card["scope"] == "builtin"
    assert protocol_card["protocol"]["is_builtin"] is True
    assert grouped["counts"] == {"saved_notes": 1, "reference_notes": 0, "total": 1}


def test_scenario_payload_cleans_empty_nested_values() -> None:
    payload = scenario_payload(
        {
            "scenario_kind": "comparison",
            "branch_workspace_ids": ["path-a", "", "path-b"],
            "empty": "",
            "nested": {"keep": "yes", "drop": ""},
        }
    )

    assert payload == {
        "scenario_kind": "comparison",
        "scenario": {
            "scenario_kind": "comparison",
            "branch_workspace_ids": ["path-a", "path-b"],
            "nested": {"keep": "yes"},
        },
    }
