# Conversation Continuity Resume Todo

## Purpose

This note tracks the work needed to make logout/login continuity robust.

User expectation:

`If I log out and log back in, I should be able to easily resume the conversation and draft I was working on.`

## Current Repo Findings

The current repo already has several continuity foundations:

- Authenticated users get isolated storage under `users/<username>/`.
- `/api/health` reports the authenticated user, active workspace id, experiment status, and auth state.
- `ActiveWorkspaceStateStore` persists the active whiteboard id.
- `WorkspaceStore` persists saved whiteboard files.
- `MemoryTraceStore` persists recent turn traces for recall and inspection.
- The frontend has scoped session snapshot logic for restoring recent turn state during the same browser session.
- Existing auth and snapshot tests cover user-scoped storage, logout protection, stale auth handling, and restored whiteboard state.

The likely gap is full conversation restoration after logout/login:

- `history` is currently sent from the client to `/api/chat`.
- The visible transcript is primarily frontend state.
- Session snapshots use `sessionStorage`, which is not a durable cross-login conversation store.
- Memory Trace persists turn summaries, but it is not yet a user-facing conversation thread restore system.

## Target Experience

- [ ] User logs out.
- [ ] User logs back into the same account.
- [ ] Vantage restores the active whiteboard or offers to reopen it.
- [ ] Vantage restores enough recent conversation context to continue naturally.
- [ ] Vantage shows a clear resume cue such as `Resume previous conversation`.
- [ ] Pending whiteboard drafts/offers are either restored safely or explicitly expired.
- [ ] Pinned context and selected/referenced records are either restored or clearly cleared.
- [ ] Experiment mode resumes only when the same user had an active experiment session.
- [ ] A different user never sees another user's transcript, whiteboard, Memory Trace, or draft state.

## Product Rules

- [ ] Resume should feel easy, not automatic in a surprising way.
- [ ] The user should know whether they are resuming a durable conversation, an experiment session, or only a saved whiteboard.
- [ ] Hidden whiteboard content should not silently ground ordinary chat after login unless the user resumes it or it is visibly in scope.
- [ ] Recent conversation replay should stay bounded.
- [ ] Resume should not require loading the entire Memory Trace history into the model.
- [ ] Logout should clear local UI state for privacy, but not delete durable per-user state.

## Backend Tasks

- [ ] Decide whether to introduce a first-class conversation/thread store or reconstruct resume state from Memory Trace.
- [ ] Add an authenticated resume endpoint, for example `GET /api/session/resume`.
- [ ] Return a safe resume payload:
  - active user id
  - active workspace id and title
  - active workspace lifecycle
  - recent turn summaries
  - last assistant/user messages suitable for transcript restore
  - pinned context id when still valid
  - active experiment status
  - pending whiteboard state only if safe and fresh
- [ ] Keep the payload bounded by count and age.
- [ ] Ensure resume payload is user-scoped.
- [ ] Ensure experiment-mode resume reads from the active experiment session, not durable state alone.
- [ ] Add server tests for logout/login resume behavior.

## Frontend Tasks

- [ ] After login, request resume state before showing the default welcome message.
- [ ] Render a gentle resume prompt when prior state exists.
- [ ] Restore visible transcript from safe recent-turn summaries.
- [ ] Restore active whiteboard metadata and content when appropriate.
- [ ] Restore or clear pinned context explicitly.
- [ ] Avoid restoring stale pending whiteboard offers without a freshness check.
- [ ] Keep logout clearing local UI state for privacy.
- [ ] Add frontend state tests for login resume and cross-user isolation.

## Test Matrix

- [ ] Same user logs out and back in: active whiteboard is available.
- [ ] Same user logs out and back in: recent transcript can be resumed.
- [ ] Same user logs out and back in: next turn includes appropriate recent context.
- [ ] Same user logs out and back in with an unsaved transient draft: user sees recover/reopen option.
- [ ] Same user logs out and back in with a pending whiteboard offer: stale offer does not silently apply.
- [ ] Same user logs out and back in during experiment mode: experiment session is accurately reported.
- [ ] Different user logs in after logout: no previous user's state is visible.
- [ ] Expired session challenge: local UI clears, but re-login offers safe resume.
- [ ] Browser refresh while logged in: existing snapshot behavior still works.
- [ ] Server restart: durable resume still works from persisted state, except intentionally in-memory secrets.

## Existing Tests Run

Focused checks run on 2026-04-29:

- [x] `.venv/bin/python -m pytest tests/test_server.py -k 'login or auth or user_scoped or create_account'`
  - Result: 6 passed.
- [x] `node --test tests/webapp_state_model.test.mjs --test-name-pattern 'auth|restore|workspace reconciliation'`
  - Result: 23 passed.

These confirm existing auth, user-scoped storage, auth challenge handling, and frontend restore helpers. They do not yet prove full conversation-thread resume after logout/login.

## Open Questions

- [ ] Should conversation resume be reconstructed from Memory Trace or stored as a separate thread snapshot?
- [ ] How many turns should be restored into the visible transcript?
- [ ] Should restored transcript messages be visually marked as restored history?
- [ ] Should pending whiteboard offers survive logout, and if so for how long?
- [ ] Should unsaved local drafts be recoverable after logout, or only after refresh within the same authenticated session?
- [ ] Should the model receive restored transcript context automatically, or only after the user accepts resume?

## Definition Of Done

- [ ] Logout clears private local UI state.
- [ ] Re-login restores or offers to restore the user's active work.
- [ ] The next chat turn has enough bounded continuity to feel natural.
- [ ] Cross-user privacy is protected.
- [ ] Experiment and durable modes resume accurately.
- [ ] Tests cover same-user resume, cross-user isolation, stale pending draft behavior, and server restart persistence.
