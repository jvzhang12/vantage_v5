from __future__ import annotations

from vantage_v5.services.turn_staging import StageProgressEvent
from vantage_v5.services.turn_staging import TurnStage
from vantage_v5.services.turn_staging import audit_stage_output
from vantage_v5.services.turn_staging import payload_for_progress
from vantage_v5.services.turn_staging import sanitize_public_value


def test_turn_stage_sanitizes_contract_and_bounds_max_attempts() -> None:
    stage = TurnStage(
        stage_id="Draft Stage",
        task_kind="Whiteboard Draft",
        max_attempts=99,
        reason="Prepare a whiteboard draft.",
        contract={
            "workspace_update_type": "draft_whiteboard",
            "schema": {"hidden": True},
            "provider": "openai",
            "required_fields": ["assistant_message"],
        },
    )

    payload = stage.to_payload()
    assert {
        key: payload[key]
        for key in ("stage_id", "task_kind", "contract", "max_attempts", "reason")
    } == {
        "stage_id": "draft_stage",
        "task_kind": "whiteboard_draft",
        "contract": {
            "workspace_update_type": "draft_whiteboard",
            "required_fields": ["assistant_message"],
        },
        "max_attempts": 3,
        "reason": "Prepare a whiteboard draft.",
    }


def test_stage_progress_event_hides_reasoning_provider_schema_and_debug_details() -> None:
    event = StageProgressEvent(
        event_id="offer",
        status="started",
        label="Preparing offer",
        message="Checking whiteboard affordance.",
    )

    payload = event.to_payload()
    payload["details"] = payload_for_progress(
        {
            "provider": "openai",
            "schema": {"type": "object"},
            "debug": "raw response",
            "visible": "kept",
            "nested": {"reasoning": "hidden", "count": 2},
        }
    )

    assert payload["details"] == {"visible": "kept", "nested": {"count": 2}}
    assert "provider" not in str(payload).lower()
    assert "schema" not in str(payload).lower()
    assert "debug" not in str(payload).lower()
    assert "reasoning" not in str(payload).lower()


def test_audit_accepts_whiteboard_draft_that_satisfies_contract() -> None:
    stage = TurnStage(
        stage_id="draft",
        task_kind="whiteboard_draft",
        contract={"min_content_chars": 10, "required_fields": ["assistant_message"]},
    )

    result = audit_stage_output(
        {
            "assistant_message": "I drafted it in the whiteboard.",
            "workspace_update": {
                "type": "draft_whiteboard",
                "title": "Launch Email",
                "content": "# Launch Email\n\nHi Jamie...",
            },
        },
        stage,
    )

    assert result.accepted is True
    assert result.retryable is False
    assert result.to_payload()["status"] == "accepted"


def test_audit_returns_retryable_before_attempt_budget_is_exhausted() -> None:
    stage = TurnStage(
        stage_id="offer",
        task_kind="whiteboard_offer",
        contract={"workspace_update_type": "offer_whiteboard"},
        max_attempts=2,
    )

    result = audit_stage_output(
        {"assistant_message": "I can help draft that."},
        stage,
        attempt=1,
    )

    assert result.accepted is False
    assert result.retryable is True
    assert result.terminal is False
    assert result.issues == ("Missing workspace_update object.",)
    assert result.retry_instruction == "Return an offer_whiteboard workspace_update with a public summary. Fix: Missing workspace_update object."


def test_audit_returns_terminal_when_attempt_budget_is_exhausted() -> None:
    stage = TurnStage(
        stage_id="draft",
        task_kind="whiteboard_draft",
        contract={"workspace_update_type": "draft_whiteboard"},
        max_attempts=1,
    )

    result = audit_stage_output(
        {"workspace_update": {"type": "offer_whiteboard", "summary": "I can draft it."}},
        stage,
        attempt=1,
    )

    assert result.accepted is False
    assert result.retryable is False
    assert result.terminal is True
    assert result.retry_instruction == ""
    assert result.issues == ("workspace_update.type must be draft_whiteboard.",)


def test_sanitize_public_value_drops_hidden_keys_recursively() -> None:
    assert sanitize_public_value(
        {
            "visible": "yes",
            "messages": ["hidden"],
            "items": [{"debug": "hidden", "name": "kept"}],
            "empty": "",
        }
    ) == {"visible": "yes", "items": [{"name": "kept"}]}
