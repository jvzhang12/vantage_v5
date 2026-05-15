from __future__ import annotations

import json

from vantage_v5.services.capabilities import build_app_capability_manifest
from vantage_v5.services.artifact_mutation_compiler import app_json_interface_for_turn
from vantage_v5.services.chat import app_capabilities_prompt_payload
from vantage_v5.services.chat import _extract_workspace_signal


def test_artifact_update_json_creates_whiteboard_draft() -> None:
    payload = {
        "assistant_message": "I updated the draft in the whiteboard.",
        "artifact_update": {
            "artifact_kind": "whiteboard",
            "operation": "replace_content",
            "title": "Launch Note",
            "summary": "Replaced the whiteboard content from JSON.",
            "content_markdown": "# Launch Note\n\nUpdated draft body.",
        },
    }

    message, draft, offer = _extract_workspace_signal(
        f"ARTIFACT_UPDATE_JSON: {json.dumps(payload)}",
        whiteboard_mode="draft",
    )

    assert message == "I updated the draft in the whiteboard."
    assert offer is None
    assert draft is not None
    assert draft.summary == "Replaced the whiteboard content from JSON."
    assert draft.content == "# Launch Note\n\nUpdated draft body."


def test_artifact_update_json_is_ignored_for_chat_mode() -> None:
    payload = {
        "assistant_message": "I can describe the edit here.",
        "artifact_update": {
            "artifact_kind": "whiteboard",
            "operation": "replace_content",
            "content_markdown": "# Should Not Open",
        },
    }

    message, draft, offer = _extract_workspace_signal(
        f"ARTIFACT_UPDATE_JSON: {json.dumps(payload)}",
        whiteboard_mode="chat",
    )

    assert message == "I can describe the edit here."
    assert draft is None
    assert offer is None


def test_main_chat_capability_prompt_omits_mutation_json_contract() -> None:
    manifest = build_app_capability_manifest()

    payload = app_capabilities_prompt_payload(manifest)

    assert payload is not None
    assert "artifact_json_contract" not in payload
    assert all("json_interface" not in app for app in payload["apps"])
    assert "whiteboard.update_content" in {tool["name"] for tool in payload["tools"]}


def test_second_step_app_interface_includes_relevant_json_contract() -> None:
    manifest = build_app_capability_manifest()

    payload = app_json_interface_for_turn(
        manifest,
        user_message="replace Advisor check-in with Grocery shopping",
        semantic_action="Understood. I will replace Advisor check-in with Grocery shopping.",
        visible_artifacts=[{"kind": "calendar_day"}],
    )

    assert [app["id"] for app in payload["apps"]] == ["calendar"]
    assert payload["apps"][0]["json_interface"]["artifact_kind"] == "calendar"
    assert "calendar.replace_event" in {tool["name"] for tool in payload["tools"]}
