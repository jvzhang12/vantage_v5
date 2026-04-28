# `tests/test_context_support.py`

Focused unit tests for the context support collaborator.

## Purpose

- Verify workspace and pending-whiteboard helper behavior independently from `ContextEngine` and `/api/chat`.
- Lock down hidden whiteboard safety at the collaborator boundary.

## Coverage

- Workspace scope normalization for explicit scope values, live buffers, explicit whiteboard requests, and excluded defaults.
- Unsaved buffer construction, scenario metadata recovery, and hidden-context redaction.
- Buffered workspace overlays that preserve existing scenario metadata when the browser buffer omits it.
- Pending whiteboard normalization, type/status alias bridging, narrow carry acceptance, stale/fresh request rejection, and origin-message safety.
- Whiteboard entry-mode classification for hidden, prior-material, continued-current, and fresh-start cases.
