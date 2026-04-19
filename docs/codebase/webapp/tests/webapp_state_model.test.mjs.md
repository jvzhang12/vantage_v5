# `tests/webapp_state_model.test.mjs`

Focused regression tests for the webapp state helpers and normalization layer.

## Purpose

- Verify the surface-state enum behavior.
- Verify workspace-context scoping for chat requests.
- Verify response-mode, learned-item, record-id, interpretation, and workspace-update normalization against the canonical backend DTO contract, including direct `groundingMode`, canonical recall alias handling, `contextSources`, returned whiteboard-scope handling, and the richer interpretation fields used by the staged `Reasoning Path`.
- Verify the turn-payload normalization keeps the returned `memory_trace_record` available to the client.
- Verify dirty local whiteboards survive passive refresh rules.
- Cover the distinction between “can return to whiteboard” and “whiteboard is in scope,” plus the backend-matched pending-draft carry contract, forced scope overrides, and dirty-snapshot defaults that preserve transient drafts.
- Cover the turn-panel grounding copy helper so the normal Vantage dock/meta labels stay aligned across the six grounding cases plus the idle and learned-only fallback branches.

## Why It Matters

- This is the main guardrail against brittle client-state and payload-contract regressions, especially around surface transitions, whiteboard scoping, and turn normalization.
