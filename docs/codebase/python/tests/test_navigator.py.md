# `tests/test_navigator.py`

Focused unit tests for the Navigator interpretation boundary.

## Purpose

- Lock down the deterministic normalization applied after the Navigator LLM returns a control-panel plan.
- Keep unsupported model-proposed actions and unsupported protocol kinds from leaking into later execution layers.

## Coverage

- Control-panel normalization drops unknown action types, drops `apply_protocol` actions with unsupported protocol kinds, preserves supported protocol actions including `remember`, normalizes legacy `kind` into `protocol_kind`, clears `protocol_kind` on non-protocol actions, and normalizes structured `close_surface` / `preserve_surface` targets/confidence.
- Fallback Navigator decisions use the canonical `respond` action shape with `protocol_kind: null`.
- Decision stabilization recovers canonical behavior when the model underspecifies obvious work-product turns: email drafting gets an email protocol plus whiteboard offer, chat-only email stays in chat while keeping the protocol, and active email draft revisions go straight to draft mode.
- Saved/open-material control-plane fallback adds explicit `surface_to_open="whiteboard"` plus an `open_whiteboard` action when a lookup prompt selected a saved artifact but omitted the UI open signal. Explicit memory fallback adds a `remember` action and clears accidental operational surface opens for clear `remember that ...` turns, while ordinary artifact Q&A and keep/leave-open visible-surface language remain chat-only with no UI replacement.
