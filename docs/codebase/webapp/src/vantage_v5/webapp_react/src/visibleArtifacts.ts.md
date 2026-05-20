# `src/vantage_v5/webapp_react/src/visibleArtifacts.ts`

Visible artifact context builder for React.

## Purpose

- Convert the current visible surface and whiteboard into markdown-shaped context for `/api/chat`.
- Ensure model calls reflect the user’s current artifact view.

## Coverage

- Calendar week, calendar day, today briefing, task focus, and whiteboard visible-context payloads.
- Calendar week markdown includes the active week’s days and events, so switching weeks changes the next model-call context.
- The builder can now consume explicit `visibleSurfaces` state, so cached surfaces and selected resources are not serialized as visible context unless the reducer says they are actually visible.
