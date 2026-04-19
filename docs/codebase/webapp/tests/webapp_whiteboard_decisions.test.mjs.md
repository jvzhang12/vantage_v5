# `tests/webapp_whiteboard_decisions.test.mjs`

Focused tests for the pending-whiteboard decision UI.

## Purpose

- Verify when whiteboard decisions are visible under the canonical surface enum.
- Verify local destructive-open decisions show the right replace/keep choices.
- Verify server-supplied whiteboard offers and drafts render the right action set.
- Verify non-destructive replace/append/keep-current choices for pending drafts and the fallback from stale local decision state back to server-provided whiteboard decisions.
- Verify resolved server decisions stay hidden once the user already chose a path.

## Why It Matters

- These tests keep the whiteboard workflow legible and non-destructive.
