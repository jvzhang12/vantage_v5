# `src/vantage_v5/services/context_support.py`

Context-preparation support collaborator for workspace, pending whiteboard, and whiteboard-entry helpers.

## Purpose

- Keep storage-shaped workspace helper behavior out of `ContextEngineHooks`.
- Centralize workspace scope normalization, live-buffer document construction, hidden whiteboard redaction, pending whiteboard normalization/carry checks, and whiteboard entry-mode classification.
- Delegate narrow phrase matching to `WhiteboardRoutingEngine` instead of adding broad deterministic intent sorting.

## Key Classes

- `ContextSupport`: pure support object used by `ContextEngine` during turn preparation.

## Notable Behavior

- `workspace_scope="excluded"` can still preserve workspace identity and scenario metadata while redacting body content.
- Unsaved browser buffers are converted into `WorkspaceDocument` instances without persisting workspace files.
- Pending whiteboard payloads bridge legacy `type` and canonical `status`, but only carry when the narrow whiteboard follow-up rules accept the user message.
