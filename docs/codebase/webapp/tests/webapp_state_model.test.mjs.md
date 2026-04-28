# `tests/webapp_state_model.test.mjs`

Focused regression tests for the webapp state helpers and normalization layer.

## Purpose

- Verify the surface-state enum behavior.
- Verify workspace-context scoping for chat requests.
- Verify deictic whiteboard reopen resolution for follow-ups that should reopen a uniquely recalled durable item instead of drafting against the currently open whiteboard.
- Verify response-mode, learned-item, pinned-context, record-id, interpretation, semantic-frame, semantic-policy, protocol metadata, system-state, activity, and workspace-update normalization against the canonical backend DTO contract, including direct `groundingMode`, canonical recall alias handling, returned learned-item correction metadata such as `scope`, `durability`, `why_learned`, and `correction_affordance`, returned whiteboard-scope handling, the richer interpretation fields used by the staged `Reasoning Path`, and the semantic-frame fields used by the compact Inspect understanding cue.
- Verify semantic action and clarification copy helpers stay concise and display-ready while remaining unwired from the DOM.
- Verify the turn-payload normalization keeps the returned `memory_trace_record` available to the client.
- Verify dirty local whiteboards survive passive refresh rules.
- Verify workspace snapshots preserve the whiteboard-owned latest durable artifact cue used by the new E1-A whiteboard save affordance.
- Verify the boot-only restore/load reconciliation keeps unsaved drafts while clearing stale inspection state when the restore came from the scope-scoped fallback or the loaded workspace replaced the restored one, including blank-to-saved workspace-anchor changes, harmless title-only normalization that should preserve continuity, and same-id whiteboard replacements whose content changed underneath the user.
- Cover the distinction between “can return to whiteboard” and “whiteboard is in scope,” plus the backend-matched pending-draft carry contract, including the narrow explicit-whiteboard carveout, forced scope overrides, and dirty-snapshot defaults that preserve transient drafts.
- Cover the restore split between workspace-scoped snapshots, which may restore the full inspection state, and scope-scoped fallback snapshots, which keep pinned context, preserve the original `workspaceContextScope`, but clear stale selected-record state and collapse any stale `Vantage` reopen.
- Cover Scenario Lab comparison normalization so the client can preserve the saved comparison artifact’s indexed branch roster and treat the artifact itself as the durable revisit hub even when the branch list is sparse or when the UI has to derive a richer roster from normalized branch cards.
- Cover the shared Scenario Lab branch-index helper directly so the fallback roster path stays safe when the renderer needs to derive branch cards or plain workspace ids.
- Cover the turn-panel grounding copy helper so the normal Vantage dock/meta labels stay aligned across the six grounding cases plus the idle and learned-only fallback branches.

## Why It Matters

- This is the main guardrail against brittle client-state and payload-contract regressions, especially around surface transitions, whiteboard scoping, and turn normalization.
