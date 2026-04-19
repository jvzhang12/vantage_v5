# `src/vantage_v5/webapp/turn_payloads.mjs`

Normalization layer between backend payload DTOs and the client’s rendering state.

## Purpose

- Convert backend response-mode payloads into stable client-facing state without re-inventing client-only grounding kinds.
- Normalize Scenario Lab payloads into a UI-ready comparison model so the webapp can surface question, recommendation, parsed branch details, and saved-comparison details without reparsing Markdown everywhere.
- Normalize turn interpretation metadata from navigator/server output.
- Normalize `workspace_update` payloads into the client’s pending-offer / pending-draft shape.
- Normalize the returned `memory_trace_record` payload so the client can render the created turn trace without re-inventing backend DTO fallbacks.

## Key Functions

- `normalizeResponseMode()`
- `normalizeScenarioLabPayload()`
- `normalizeLearnedItems()`
- `normalizeMemoryTraceRecord()`
- `normalizeRecordId()`
- `normalizeTurnPayload()`
- `normalizeTurnInterpretation()`
- `normalizeWorkspaceUpdate()`

## Notable Behavior

- Preserves the backend contract directly: `kind` stays `grounded`, `best_guess`, or `idle`, while `groundingMode` and `contextSources` carry the more specific source path and the normalized client shape now prefers recall-facing labels.
- Keeps the canonical grounding-source list narrow: `recall`, `whiteboard`, `recent_chat`, and `pending_whiteboard`. `memory_trace` is not a separate `response_mode` grounding source here; it enters the UI through recalled items and `memory_trace_record`.
- Keeps the backend’s user-facing grounding copy intact across normalization, including source-specific mixed-context labels like `Recall + Recent Chat` and support notes like `No grounded context supported this answer.`
- Falls back conservatively: if the backend omits `response_mode`, the client only infers recall grounding from an explicit recalled-item count and otherwise stays `idle` instead of fabricating a best-guess claim.
- Keeps a narrow compatibility shim for older snapshot payloads that still use legacy values such as `working_memory_grounded` or `working_memory`, but normalizes them into the canonical recall-facing shape for the rest of the client.
- Parses the Markdown-heavy Scenario Lab branch and comparison bodies into section-wise lists and text blocks so `app.js` can consume a stable comparison/branch view-model first, while still keeping a small renderer-side fallback path for legacy or partial payloads.
- Centralizes the remaining C3 compatibility shims for `learned` versus `created_record`, `record_id` versus `concept_id`, and returned `workspace.context_scope`, so `app.js` and the identity helpers do not each re-implement those fallbacks.
- Exposes a small `normalizeTurnPayload()` helper that packages the canonical turn-facing pieces the webapp actually consumes directly: normalized recall items, normalized response mode, normalized learned items, normalized `memoryTraceRecord`, normalized Scenario Lab state, normalized workspace updates, and the returned whiteboard scope disclosure.
- Leaves candidate trace arrays and selected trace-note arrays outside `normalizeTurnPayload()`. `app.js` normalizes those through its generic memory-item path because they render as cards, not as response-mode DTOs.
- Preserves the richer interpretation DTO fields the staged `Reasoning Path` now uses directly, including `requestedWhiteboardMode` and `selectedRecordReason`, instead of flattening route decisions down to only mode, reason, and confidence.
- Depends on `whiteboard_decisions.mjs` to understand whether a workspace update has already been resolved.
