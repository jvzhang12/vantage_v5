# `tests/test_turn_plan.py`

Focused unit tests for internal TurnPlan trace, surface-authority, and write-ledger contracts.

## Purpose

- Verify that `TurnPlanBuilder` projects finalized request/response fields into a stable internal plan without changing public payload behavior.
- Verify that `build_turn_plan_surface_authority()` derives the execution-facing surface-action view used by the orchestrator and server for open-only, close, preserve, and operational-surface post-processing.
- Verify that the trace-only `write_ledger` classifies finalized write/no-write response fields without changing execution.
- Cover the TurnPlan slices independently from the full `/api/chat` execution path.

## Coverage

- Chat-only Q&A records no UI-open action and no write intent.
- Saved artifact open-only turns record a Whiteboard UI action, selected artifact target, no-write side-effect policy, and `open_only_no_write` ledger entry.
- Surface-authority tests assert that Whiteboard `open_only`, nested close `surface_action` payloads, and preserve/no-op invocations suppress automatic graph writes and artifact actions, while calendar/task operational surfaces still allow payload construction.
- Explicit Whiteboard draft turns record draft write intent and workspace-update allowance.
- Write-ledger coverage records `none`, `open_only_no_write`, `pending_whiteboard_offer`, `pending_whiteboard_draft`, `draft_snapshot_workspace_update`, `artifact_save_or_promotion`, `concept_write`, `memory_write`, `proposed_calendar_task_mutation`, and `accepted_calendar_task_mutation` categories.
- Today/calendar turns record read-only operational surface intent and surface-payload policy.
- Visible artifact Q&A records chat-first/no-write policy.
- Preserve-visible-surface turns record no UI-open action and no-write side-effect policy.
- Validation coverage verifies clean turns produce no warnings and contradictory finalized payloads warn for selected context opening without authority, open-only writes, invalid saved-artifact open targets, UI-open target/primary-resource conflicts, visible/selected-artifact Q&A writes, preserve reclassification, close reclassification/writes/deletes, operational surface payload mismatch, and non-proposal/confirmation-skipping calendar/task mutation.
- Final response trace payloads include `final_response.turn_plan.write_ledger` and `final_response.turn_plan.validation`.
