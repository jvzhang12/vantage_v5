# `src/vantage_v5/services/turn_staging.py`

Pure staging-contract helpers for Navigator-as-stager turn execution.

## Purpose

- Represent a staged turn contract as a small public-safe `TurnStage` payload.
- Represent user-visible staging progress without provider, schema, debug, prompt, or hidden reasoning leakage.
- Audit parsed chat output against a staged contract without making provider calls.
- Preserve compatibility with the orchestration-facing staging helpers used by ChatService retries.

## Key Classes / Functions

- `TurnStage`: typed staged-turn contract with normalized `stage_id`, `task_kind`, bounded `max_attempts`, public summary/reason, retryability, metadata, and a sanitized string or dictionary contract.
- `StageProgressEvent`: typed progress event for user-visible stage activity; `to_dict()` / `to_payload()` sanitize labels and messages.
- `StageAuditResult`: accepted/retry/terminal audit result with issue list, retryability helpers, and public payload serialization.
- `build_turn_stage()`: compatibility helper that derives the current chat/scenario/whiteboard stage from Navigator mode and whiteboard mode.
- `stage_progress_event()` / `initial_stage_progress()`: convenience builders for orchestration progress payloads.
- `audit_stage_response()`: compatibility helper for existing ChatService surface checks.
- `audit_stage_output()`: pure parsed-output auditor for staged contracts, including `draft_whiteboard` and `offer_whiteboard` expectations.
- `payload_for_stage()`, `payload_for_progress()`, `payload_for_audit()`: payload-normalizer helpers used by `turn_payloads.py`.
- `sanitize_public_value()` / `sanitize_stage_text()`: recursive public sanitizers for staging fields.

## Notable Behavior

- `max_attempts` is clamped to the supported public retry budget.
- Hidden/provider/debug/schema/reasoning fields are dropped recursively before payload assembly.
- Draft audits require a `workspace_update` with `type="draft_whiteboard"`, title, and content.
- Offer audits require a `workspace_update` with `type="offer_whiteboard"` and a public summary.
- Failed audits become retryable until the stage attempt budget is exhausted, then terminal.
