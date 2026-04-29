# `tests/test_navigator.py`

Focused unit tests for the Navigator interpretation boundary.

## Purpose

- Lock down the deterministic normalization applied after the Navigator LLM returns a control-panel plan.
- Keep unsupported model-proposed actions and unsupported protocol kinds from leaking into later execution layers.

## Coverage

- Control-panel normalization drops unknown action types, drops `apply_protocol` actions with unsupported protocol kinds, preserves supported protocol actions, normalizes legacy `kind` into `protocol_kind`, and clears `protocol_kind` on non-protocol actions.
- Fallback Navigator decisions use the canonical `respond` action shape with `protocol_kind: null`.
- Decision stabilization recovers canonical behavior when the model underspecifies obvious work-product turns: email drafting gets an email protocol plus whiteboard offer, chat-only email stays in chat while keeping the protocol, and active email draft revisions go straight to draft mode.
