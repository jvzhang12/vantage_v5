# `src/vantage_v5/webapp_react/src/appReducer.test.ts`

Vitest coverage for the React app reducer.

## Purpose

- Lock down core migration behavior independent of React rendering.

## Coverage

- Chat success stores backend continuity history while the UI model keeps the latest answer.
- Returned artifact surfaces become active and move the app into artifact view.
- Navigator-selected saved artifacts, including artifacts selected behind an already-visible Today surface, become visible Whiteboard content, and that content is included in the next visible-artifact context without creating a separate persisted artifact surface.
