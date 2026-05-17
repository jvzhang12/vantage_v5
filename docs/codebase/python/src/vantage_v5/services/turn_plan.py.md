# `src/vantage_v5/services/turn_plan.py`

Internal TurnPlan observability DTOs for Vantage chat turns.

## Purpose

- Build a typed, trace-safe `TurnPlan` from already-finalized `/api/chat` request and response fields.
- Capture retrieval selection, explicit UI surface intent, write/draft intent, visible context, side-effect policy, semantic/protocol summaries, execution policy, compatibility links, and trace-only validation warnings without changing runtime behavior.
- Keep the first TurnPlan slice observability-only: no routing, retrieval, frontend, or write paths consume the plan yet.

## Key Classes / Functions

- `TurnPlan`: top-level frozen dataclass with `request`, `route`, `retrieval`, `visible_context`, `ui_surface_action`, `write_intent`, `side_effect_policy`, `protocols`, `semantic`, `execution`, `compatibility`, and `validation` sections.
- `TurnPlanValidation`: trace-only warning container used to compare finalized TurnPlan sections against the final public response fields.
- `TurnPlanBuilder`: builds a `TurnPlan` from a final trace request payload plus the final public response payload.
- `turn_plan_trace_payload()`: convenience helper used by final-response trace persistence.

## Notable Behavior

- Selected attention resources are compacted for TurnPlan traces; full resource content is not duplicated inside the plan.
- Whiteboard `open_only` is recorded as a UI-only action and a no-write side-effect policy, but this module does not enforce that policy.
- Final `surface_action` close directives are recorded as UI surface actions with a no-write side-effect policy, but this module remains observability-only and does not apply the close.
- `preserve_visible_surface` invocations are recorded as no-op UI preservation with a no-write side-effect policy.
- Visible/selected artifact Q&A is recorded as chat-first/no-write policy when the existing `surface_invocation.intent` already says the turn was a current-artifact or selected-material follow-up.
- Validation warnings are non-authoritative diagnostics only. They flag contradictions such as selected context opening a UI surface without explicit open authority, `open_only` carrying writes, saved-artifact opens that lack a selected openable target, UI open targets that conflict with the selected primary resource, preserve/close turns being reclassified or carrying side effects, visible/selected-artifact Q&A writing without explicit write authority, draft surface mismatches, operational active-surface/payload mismatches, and calendar/task mutations that are not proposal-only/confirmation-gated.
- Public compatibility fields remain unchanged; TurnPlan records where existing fields such as `navigator_selection`, `surface_invocation`, `workspace_update`, `graph_action`, `created_record`, and `artifact_actions` appeared in the final response.
