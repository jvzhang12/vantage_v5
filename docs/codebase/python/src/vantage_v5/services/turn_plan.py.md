# `src/vantage_v5/services/turn_plan.py`

Internal TurnPlan DTOs for Vantage chat turns.

## Purpose

- Build a typed, trace-safe `TurnPlan` from already-finalized `/api/chat` request and response fields.
- Capture retrieval selection, explicit UI surface intent, write/draft intent, visible context, side-effect policy, semantic/protocol summaries, execution policy, compatibility links, and trace-only validation warnings without changing runtime behavior.
- Provide the first authoritative TurnPlan execution helper for UI surface actions only. Open/close/preserve surface application can consume `TurnPlanSurfaceAuthority`; routing, retrieval, frontend behavior, and write/draft execution still use their existing paths.

## Key Classes / Functions

- `TurnPlan`: top-level frozen dataclass with `request`, `route`, `retrieval`, `visible_context`, `ui_surface_action`, `write_intent`, `side_effect_policy`, `protocols`, `semantic`, `execution`, `compatibility`, and `validation` sections.
- `TurnPlanSurfaceAuthority`: narrowed execution-facing view derived from TurnPlan surface, write, and side-effect fields. It centralizes whether a surface turn is close, preserve, or Whiteboard open-only; whether auto graph writes and artifact actions must be suppressed; and whether operational surface payloads should be built.
- `TurnPlanValidation`: trace-only warning container used to compare finalized TurnPlan sections against the final public response fields.
- `TurnPlanBuilder`: builds a `TurnPlan` from a final trace request payload plus the final public response payload.
- `build_turn_plan_surface_authority()`: builds the internal surface-action authority from finalized or in-flight response fields, including nested `surface_invocation.surface_action` compatibility payloads.
- `turn_plan_trace_payload()`: convenience helper used by final-response trace persistence.

## Notable Behavior

- Selected attention resources are compacted for TurnPlan traces; full resource content is not duplicated inside the plan.
- Whiteboard `open_only` is recorded as a UI-only action and a no-write side-effect policy. The narrowed surface-authority helper is now consumed by the orchestrator and server post-processing to keep this path chat/no-write.
- Final `surface_action` close directives are recorded as UI surface actions with a no-write side-effect policy. The narrowed surface-authority helper is now consumed to apply close acknowledgements and suppress downstream write/action compilation.
- `preserve_visible_surface` invocations are recorded as no-op UI preservation with a no-write side-effect policy and no operational surface payloads.
- Visible/selected artifact Q&A is recorded as chat-first/no-write policy when the existing `surface_invocation.intent` already says the turn was a current-artifact or selected-material follow-up.
- TurnPlan is authoritative only for surface action application in this slice. Write/draft/save decisions remain on the existing semantic policy, Whiteboard routing, chat, and artifact mutation paths.
- Validation warnings are non-authoritative diagnostics only. They flag contradictions such as selected context opening a UI surface without explicit open authority, `open_only` carrying writes, saved-artifact opens that lack a selected openable target, UI open targets that conflict with the selected primary resource, preserve/close turns being reclassified or carrying side effects, visible/selected-artifact Q&A writing without explicit write authority, draft surface mismatches, operational active-surface/payload mismatches, and calendar/task mutations that are not proposal-only/confirmation-gated.
- Public compatibility fields remain unchanged; TurnPlan records where existing fields such as `navigator_selection`, `surface_invocation`, `workspace_update`, `graph_action`, `created_record`, and `artifact_actions` appeared in the final response.
