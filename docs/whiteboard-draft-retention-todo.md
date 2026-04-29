# Whiteboard Draft Retention Todo

## Purpose

This note tracks the implementation work for recoverable whiteboard drafts with retention limits.

The product rule is:

`Nothing should be lost, but not everything should be remembered.`

Whiteboard drafts should be auto-saved for recovery, but they should not automatically become memories, concepts, or fully promoted artifacts. Explicit save and promotion should remain the moment when Vantage treats a draft as intentionally durable Library material.

## Current Repo Context

The current repo already distinguishes:

- `Whiteboard`: live collaborative draft surface
- `artifacts/`: concrete saved outputs and whiteboard snapshots
- `memories/`: retained continuity facts
- `concepts/`: durable reusable knowledge
- `workspaces/`: implementation storage for whiteboard documents and branch workspaces

Existing docs also describe automatic artifact snapshots for concrete whiteboard draft iterations. This todo is narrower: it covers recovery and cleanup behavior for transient or recent whiteboard drafts so the user does not lose work, while the Library does not become noisy by default.

## Target Lifecycle

- [ ] `active_whiteboard`: currently open draft, auto-saved for recovery.
- [ ] `recent_draft`: inactive but recoverable whiteboard draft.
- [ ] `expiring_draft`: recoverable draft approaching retention deletion.
- [ ] `saved_whiteboard`: user intentionally saved a whiteboard snapshot.
- [ ] `promoted_artifact`: user intentionally promoted the draft into durable artifact state.
- [ ] `derived_concept`: user intentionally distilled reusable knowledge from the draft.

## Product Rules

- [ ] Auto-save protects against refreshes, crashes, navigation, and app restarts.
- [ ] Auto-save does not by itself create a memory or concept.
- [ ] Auto-save does not by itself mean the draft should appear as a durable Library item.
- [ ] Saved whiteboards and promoted artifacts should keep clear lifecycle labels.
- [ ] Users should be warned before recoverable drafts are deleted by retention policy.
- [ ] Users should be able to keep, promote, delete, or let expiring drafts expire.
- [ ] Retention cleanup should never delete the currently active visible whiteboard.

## Storage Tasks

- [ ] Add workspace-level metadata for retention:
  - `created_at`
  - `updated_at`
  - `last_opened_at`
  - `expires_at`
  - `retention_status`
  - `pinned`
  - `saved_snapshot_id`
  - `promoted_artifact_id`
- [ ] Decide whether retention metadata belongs in workspace frontmatter, sidecar state, or a small draft registry.
- [ ] Preserve compatibility with existing `workspaces/` Markdown files.
- [ ] Keep user-profile isolation intact under `users/<username>/`.
- [ ] Keep experiment-mode draft retention session-local unless explicitly promoted.

## Backend Tasks

- [ ] Add a draft-retention service boundary rather than scattering cleanup logic through `server.py`.
- [ ] Add API support for listing recent and expiring drafts.
- [ ] Add API support for retention actions:
  - `keep`
  - `promote`
  - `delete`
  - `let_expire`
- [ ] Add a cleanup path that applies count-based and age-based retention.
- [ ] Make cleanup dry-run-able so the UI can warn before deletion.
- [ ] Ensure cleanup skips active, pinned, saved, or promoted drafts.
- [ ] Include retention status in safe `system_state` without leaking hidden draft content.

## Frontend Tasks

- [ ] Surface a quiet notice when drafts are nearing expiration.
- [ ] Add review affordances for expiring drafts.
- [ ] Add actions for `Keep`, `Promote`, `Delete`, and `Let expire`.
- [ ] Keep the notice low-friction so normal chat does not feel interrupted.
- [ ] Show lifecycle state clearly in the whiteboard UI.
- [ ] Keep transient drafts visually distinct from saved whiteboards and promoted artifacts.

## Retention Policy Defaults

Initial defaults to consider:

- [ ] Keep the most recent 25 recoverable drafts.
- [ ] Keep recoverable drafts for 30 days.
- [ ] Warn 7 days before deletion.
- [ ] Never delete a draft updated in the last 24 hours.
- [ ] Never delete pinned drafts.
- [ ] Let local configuration override count and age limits later.

## Tests To Add

- [ ] Storage tests for retention metadata parsing and compatibility with legacy workspaces.
- [ ] Backend tests for listing recent and expiring drafts.
- [ ] Backend tests for dry-run cleanup.
- [ ] Backend tests that active, pinned, saved, promoted, and experiment-local drafts are protected.
- [ ] Frontend state tests for warning display and retention actions.
- [ ] End-to-end regression test that auto-saved recovery does not create memories or concepts.

## Open Questions

- [ ] Should auto-saved transient drafts live only in `workspaces/`, or should they have a separate `drafts/` registry?
- [ ] Should artifact snapshots count against draft retention limits, or only unsaved recoverable drafts?
- [ ] Should retention cleanup run on app startup, on a timer, or only when the user opens the draft review surface?
- [ ] Should private-beta users get different retention defaults from local-only users?
- [ ] Should retained drafts be searchable by Recall, or only reopenable through draft history?

## Definition Of Done

- [ ] Whiteboard work survives ordinary refresh and restart.
- [ ] The user receives a warning before recoverable drafts are deleted.
- [ ] The user can keep or promote an expiring draft.
- [ ] The Library does not fill with transient draft noise.
- [ ] Concepts, memories, artifacts, saved whiteboards, and transient drafts remain visibly distinct.
