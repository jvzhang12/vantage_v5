# `src/vantage_v5/webapp_react/src/inspectionModel.ts`

Frontend adapter for the Vantage “Why this answer?” receipt.

## Purpose

- Map the backend latest-turn provenance payload into product-facing inspection sections.
- Keep raw backend DTO details out of the presentation component.
- Avoid exposing provider/debug internals or chain-of-thought.

## Coverage

- Builds summary columns, context-used rows, artifact/surface decisions, decision-path steps, and memory/action/write audit groups.
- Uses existing turn fields such as `context_budget`, `activity`, `surface_invocation`, answer basis, visible artifacts, learned records, graph actions, and workspace updates.
- Replaces raw user request text with bounded input metadata before rendering the Vantage Working Memory view.
- Sanitizes user-request-style reason strings such as explicit close/preserve prose into safe action labels before the Vantage UI renders them.
