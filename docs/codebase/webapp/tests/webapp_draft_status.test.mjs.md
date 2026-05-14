# `tests/webapp_draft_status.test.mjs`

Focused tests for draft-local operation feedback.

## Purpose

- Verify draft operation feedback uses a dedicated polite live-status node.
- Verify `workspaceMeta` is not reused as a live region while the editor changes.
- Verify draft-local success paths use inline status instead of global success toasts.
- Verify edited top-level frontend assets have bumped cache keys.

## Why It Matters

- These tests keep Draft feedback visible and accessible without letting success toasts cover primary Chat/Draft/Inspect navigation.
