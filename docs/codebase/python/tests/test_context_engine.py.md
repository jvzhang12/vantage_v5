# `tests/test_context_engine.py`

Focused unit tests for the backend Context Engine.

## Purpose

- Verify `ContextEngine.prepare_turn_context()` independently from `/api/chat`.
- Lock down hidden draft safety and pending whiteboard carry behavior at the new deep-module boundary.

## Coverage

- Excluded workspace context redacts both persisted workspace body content and unsaved browser buffer content.
- Missing excluded workspaces are prepared as empty buffers without raising.
- Pending whiteboard offers are normalized and carried when the carry predicate accepts the follow-up.
- Stale pending whiteboard offers are dropped by default.
- Forced pending updates bypass the carry predicate for explicit local-action flows.
