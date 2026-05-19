# `tests/test_turn_plan.py`

Focused unit tests for internal TurnPlan trace, surface-authority, and write-ledger contracts.

## Purpose

- Verify that `TurnPlanBuilder` projects finalized request/response fields into a stable internal plan without changing public payload behavior.
- Verify that `build_turn_plan_surface_authority()` derives the execution-facing surface-action view used by the orchestrator and server for open-only, close, preserve, and operational-surface post-processing.
- Verify that the trace-only `write_ledger` classifies finalized write/no-write response fields without changing execution, and that `write_projection` aligns structured write intent with finalized effects.
- Cover the TurnPlan slices independently from the full `/api/chat` execution path.

## Coverage

- Chat-only Q&A records no UI-open action and no write intent.
- Saved artifact open-only turns record a Whiteboard UI action, selected artifact target, no-write side-effect policy, and `open_only_no_write` ledger entry.
- Surface-authority tests assert that Whiteboard `open_only`, nested close `surface_action` payloads, preserve/no-op invocations, and structured visible/selected-artifact Q&A suppress automatic graph writes and artifact actions, while calendar/task operational surfaces still allow payload construction.
- Explicit Whiteboard draft turns record draft write intent and workspace-update allowance.
- Write-ledger coverage records `none`, `open_only_no_write`, `pending_whiteboard_offer`, `pending_whiteboard_draft`, `draft_snapshot_workspace_update`, `artifact_save_or_promotion`, `protocol_write`, `concept_write`, `memory_write`, `proposed_calendar_task_mutation`, and `accepted_calendar_task_mutation` categories.
- Write-projection coverage records semantic-policy artifact save/publish authority, memory-intent authority, structured concept authority, protocol-interpreter authority, actual write categories, intent/effect agreement, and the additive `surface_invocation.write_intent` / `write_effects` compatibility projection.
- Artifact-write-authority coverage verifies that structured semantic `artifact_save` / `artifact_publish` intent is allowed only when a current target is available, and that hard no-write surface authority such as `open_only`, close, or preserve denies those candidates.
- Memory-write-authority coverage verifies that request-level `memory_intent="remember"` and structured control-panel remember actions allow memory candidates only when persisted candidate fields are available, while hard no-write surface authority and missing/unsafe content deny them. It also verifies that raw message, assistant, and workspace text are ignored for safe-content validation, and that memory write effects without structured authority produce validation diagnostics.
- Concept-write-authority coverage verifies that existing meta `create_concept` / `create_revision` candidates are allowed only when structured control-panel or semantic concept intent is also present, persisted candidate fields are available, revision targets are present when needed, and hard no-write surface authority is absent. It also verifies that a meta concept candidate alone is denied as missing structured concept intent, and that missing/unsafe concept content and concept effects without authority are denied or diagnosed.
- Protocol-write-authority coverage verifies that structured protocol interpreter `upsert_protocol` candidates are allowed only when safe protocol content and a concrete protocol id/kind target are present, the existing protocol-write policy allows the write, and hard no-write surface authority is absent. It also verifies that protocol writes get their own ledger/projection category even though protocol persistence uses the concept store, that protocol projection strips residual memory/concept write metadata and nested surface statuses unless a separate real effect exists, and that denied protocol effects produce validation diagnostics.
- Operational-proposal-authority coverage verifies that proposed calendar/task candidates are allowed only when structured proposal candidates exist, safe content/targets are available, all candidates require confirmation, and hard no-write surface authority is absent. It also verifies that hard no-write plus a proposal candidate produces validation diagnostics and that non-confirmation-gated candidates are denied.
- Today/calendar turns record read-only operational surface intent and surface-payload policy.
- Visible/selected artifact Q&A records chat-first/no-write policy unless structured request, control-plane, semantic, or protocol-upsert write authority is present, while selected non-artifact operational context does not trigger the no-write suppression policy. Real semantic policy action names `artifact_save` and `artifact_publish` are covered as explicit write authority.
- Preserve-visible-surface turns record no UI-open action and no-write side-effect policy.
- Validation coverage verifies clean turns produce no warnings and contradictory finalized payloads warn for selected context opening without authority, open-only writes, invalid saved-artifact open targets, UI-open target/primary-resource conflicts, visible/selected-artifact Q&A writes, preserve reclassification, close reclassification/writes/deletes, operational surface payload mismatch, and non-proposal/confirmation-skipping calendar/task mutation.
- Final response trace payloads include `final_response.turn_plan.write_ledger` and `final_response.turn_plan.validation`.
