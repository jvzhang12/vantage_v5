# `tests/test_turn_plan.py`

Focused unit tests for internal TurnPlan observability.

## Purpose

- Verify that `TurnPlanBuilder` projects finalized request/response fields into a stable internal plan without changing public payload behavior.
- Cover the first TurnPlan slice independently from the full `/api/chat` execution path.

## Coverage

- Chat-only Q&A records no UI-open action and no write intent.
- Saved artifact open-only turns record a Whiteboard UI action, selected artifact target, and no-write side-effect policy.
- Explicit Whiteboard draft turns record draft write intent and workspace-update allowance.
- Today/calendar turns record read-only operational surface intent and surface-payload policy.
- Visible artifact Q&A records chat-first/no-write policy.
- Preserve-visible-surface turns record no UI-open action and no-write side-effect policy.
- Validation coverage verifies clean turns produce no warnings and contradictory finalized payloads warn for open-only writes, visible-artifact Q&A writes, preserve reclassification, close writes/deletes, selected context opening without authority, operational surface payload mismatch, and non-proposal calendar/task mutation.
- Final response trace payloads include `final_response.turn_plan.validation`.
