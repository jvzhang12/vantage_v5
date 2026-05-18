# `src/vantage_v5/services/turn_plan.py`

Internal TurnPlan DTOs for Vantage chat turns.

## Purpose

- Build a typed, trace-safe `TurnPlan` from already-finalized `/api/chat` request and response fields.
- Capture retrieval selection, explicit UI surface intent, write/draft intent, a trace-backed write ledger, visible context, side-effect policy, semantic/protocol summaries, execution policy, compatibility links, and trace-only validation warnings.
- Provide the authoritative TurnPlan helper for UI surface actions and no-write suppression. Open/close/preserve surface application can consume `TurnPlanSurfaceAuthority`; no-write turns can consume the same helper to suppress graph writes and artifact actions. Routing, retrieval, frontend behavior, and positive write/draft authorization still use their existing paths.

## Key Classes / Functions

- `TurnPlan`: top-level frozen dataclass with `request`, `route`, `retrieval`, `visible_context`, `ui_surface_action`, `write_intent`, `side_effect_policy`, `write_ledger`, `protocols`, `semantic`, `execution`, `compatibility`, and `validation` sections.
- `TurnPlanSurfaceAuthority`: narrowed execution-facing view derived from TurnPlan surface, write, and side-effect fields. It centralizes whether a surface turn is close, preserve, or Whiteboard open-only; whether writes are forbidden; the no-write reason/category; whether auto graph writes, protocol writes, local semantic save/publish actions, and artifact actions must be suppressed; and whether operational surface payloads should be built.
- `WriteLedgerPlan` / `WriteLedgerEntry`: compact trace-only ledger of finalized write effects, including no-write, open-only/no-write, pending Whiteboard offers/drafts, workspace updates, artifact saves/promotions, concept writes, memory writes, and proposed or accepted calendar/task mutations.
- `TurnPlanValidation`: trace-only warning container used to compare finalized TurnPlan sections against the final public response fields.
- `TurnPlanBuilder`: builds a `TurnPlan` from a final trace request payload plus the final public response payload.
- `build_turn_plan_surface_authority()`: builds the internal surface-action authority from finalized or in-flight response fields, including nested `surface_invocation.surface_action` compatibility payloads.
- `turn_plan_trace_payload()`: convenience helper used by final-response trace persistence.

## Notable Behavior

- Selected attention resources are compacted for TurnPlan traces; full resource content is not duplicated inside the plan.
- Whiteboard `open_only` is recorded as a UI-only action and a no-write side-effect policy. The narrowed surface-authority helper is consumed by the orchestrator and server post-processing to keep this path chat/no-write.
- Final `surface_action` close directives are recorded as UI surface actions with a no-write side-effect policy. The narrowed surface-authority helper is consumed to apply close acknowledgements and suppress downstream write/action compilation.
- `preserve_visible_surface` invocations are recorded as no-op UI preservation with a no-write side-effect policy and no operational surface payloads.
- Visible/selected artifact Q&A is recorded as chat-first/no-write policy when the existing structured `surface_invocation.intent` already says the turn was a current-artifact or selected-material follow-up, the selected/visible context is an openable artifact or Whiteboard item, and no structured write authority is present. Structured write authority includes request-level `memory_intent="remember"`, control-plane or semantic save/learn/remember fields, real semantic policy actions such as `artifact_save` and `artifact_publish`, and protocol upsert effects already produced by the protocol interpreter. Operational surfaces and ordinary non-artifact Q&A continue through the existing meta path.
- Hard no-write surface authority (`open_only`, close, or preserve) is also reflected in execution policy as disabled local semantic writes, so local `artifact_save` / `artifact_publish` handlers cannot leak write payloads into UI-only or no-op surface turns.
- `write_ledger` is built only from finalized response payload fields such as `workspace_update`, `graph_action`, `created_record`, `artifact_actions`, `surface_invocation.write_behavior`, and `surface_action`; it does not infer semantic write intent from raw user text and does not affect execution.
- TurnPlan is authoritative for surface action application and for suppressing writes on structured no-write turns. It still does not authorize or create writes; draft/save/concept/memory/artifact/calendar-task write decisions remain on the existing semantic policy, Whiteboard routing, chat, and artifact mutation paths.
- Validation warnings are non-authoritative diagnostics only. They flag contradictions such as selected context opening a UI surface without explicit open authority, `open_only` carrying writes, saved-artifact opens that lack a selected openable target, UI open targets that conflict with the selected primary resource, preserve/close turns being reclassified or carrying side effects, visible/selected-artifact Q&A writing without explicit write authority, draft surface mismatches, operational active-surface/payload mismatches, and calendar/task mutations that are not proposal-only/confirmation-gated.
- Public compatibility fields remain unchanged; TurnPlan records where existing fields such as `navigator_selection`, `surface_invocation`, `workspace_update`, `graph_action`, `created_record`, and `artifact_actions` appeared in the final response.
