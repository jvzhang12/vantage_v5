# `src/vantage_v5/webapp_react/src/appReducer.ts`

Reducer and initial state for the React Vantage app.

## Purpose

- Centralize UI state transitions with `useReducer`.
- Keep app state typed without adding Redux/Zustand.

## Coverage

- Auth bootstrap, including whether account creation requires an access code, composer state, chat lifecycle, active view, profile menu, notices, whiteboard edits, workspace save state, and surface activation.
- Chat success stores backend history while rendering only the latest assistant answer or summoned artifact.
- When backend attention selection names a saved artifact and also emits an explicit Whiteboard open directive, the reducer can foreground the Whiteboard with that selected resource content as an editable local buffer without creating a persisted surface payload or save request, even if an already-visible Today/calendar surface was the primary selected context.
- Selected attention resources remain context unless `navigator_selection.surface_to_open` requests Whiteboard or `surface_invocation.write_behavior` is `open_only` for Whiteboard.
- Backend `surface_action.close_visible_surface` directives hide the foreground Whiteboard or active operational artifact surface while keeping cached content/payloads intact, so the next chat turn serializes no visible artifact unless the user reopens it.
- The reducer now keeps `visibleSurfaces`, `whiteboardEditor`, `selectedResource`, `pinnedContext`, and `includedContext` as explicit state domains while maintaining legacy `view`, `workspace`, `activeSurfaceId`, and `surfacePayloads` compatibility fields for existing components.
- Foregrounding an operational Today/calendar/task surface clears `visibleSurfaces.whiteboardVisible` while preserving the cached whiteboard editor buffer, so hidden Whiteboard content is not serialized as visible context on later turns.
