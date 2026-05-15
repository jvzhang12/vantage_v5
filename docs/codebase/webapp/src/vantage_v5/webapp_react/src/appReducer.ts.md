# `src/vantage_v5/webapp_react/src/appReducer.ts`

Reducer and initial state for the React Vantage app.

## Purpose

- Centralize UI state transitions with `useReducer`.
- Keep app state typed without adding Redux/Zustand.

## Coverage

- Auth bootstrap, including whether account creation requires an access code, composer state, chat lifecycle, active view, profile menu, notices, whiteboard edits, workspace save state, and surface activation.
- Chat success stores backend history while rendering only the latest assistant answer or summoned artifact.
- When the backend attention selection names a saved artifact and asks to open `whiteboard`, the reducer foregrounds the Whiteboard with that selected resource content as an editable local buffer without creating a persisted surface payload or save request.
