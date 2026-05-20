# `src/vantage_v5/webapp_react/src/appReducer.test.ts`

Vitest coverage for the React app reducer.

## Purpose

- Lock down core migration behavior independent of React rendering.

## Coverage

- Chat success stores backend continuity history while the UI model keeps the latest answer.
- `CHAT_START` marks chat busy, and both success and error paths clear that busy state.
- Returned artifact surfaces become active and move the app into artifact view.
- Navigator-selected saved artifacts with an explicit Whiteboard open directive, including artifacts selected behind an already-visible Today surface, become visible Whiteboard content, and that content is included in the next visible-artifact context without creating a separate persisted artifact surface.
- Selected saved artifacts without `surface_to_open=whiteboard` or Whiteboard `open_only` remain context and do not foreground the Whiteboard.
- Backend close-visible-surface actions hide an open Whiteboard or active Today/calendar surface without clearing saved workspace content or cached surface payloads.
- Chat success stores the normalized `working_memory_view` for the latest turn while keeping the raw resource bodies out of the React-facing DTO.
- State-domain tests assert that open-only, close, preserve, selected-resource-only, and pinned-context flows update `visibleSurfaces`, `whiteboardEditor`, `selectedResource`, and `pinnedContext` independently while preserving legacy view behavior.
