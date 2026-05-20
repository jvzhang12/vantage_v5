# `src/vantage_v5/webapp_react/src/visibleArtifacts.test.ts`

Vitest coverage for React visible artifact context.

## Purpose

- Verify current artifact surfaces become inspectable/model-visible markdown.

## Coverage

- Calendar week surface markdown includes the active week and events.
- Visible artifact payloads include both active calendar context and visible whiteboard content when both are in view.
- Explicit `visibleSurfaces` state controls whether cached operational surfaces or whiteboard editor content are serialized for the next `/api/chat` request.
