# Webapp Codebase Summaries

This directory mirrors the React web client under `src/vantage_v5/webapp_react`, plus the browser-facing frontend tests.

The goal is the same as the Python summaries: let future agents understand the shipped client surfaces, state model, payload contract, and focused browser-side tests without reverse-engineering the React app from scratch.

## Suggested Reading Order

1. `src/vantage_v5/webapp_react/src/App.tsx.md`
2. `src/vantage_v5/webapp_react/src/components/Core.tsx.md`
3. `src/vantage_v5/webapp_react/src/components/Surfaces.tsx.md`
4. `src/vantage_v5/webapp_react/src/normalizers.ts.md`

## React Frontend Surface

- `src/vantage_v5/webapp_react/index.html.md`
- `src/vantage_v5/webapp_react/public/sw.js.md`
- `src/vantage_v5/webapp_react/src/App.tsx.md`
- `src/vantage_v5/webapp_react/src/api.ts.md`
- `src/vantage_v5/webapp_react/src/appReducer.ts.md`
- `src/vantage_v5/webapp_react/src/components/VantageMark.tsx.md`
- `src/vantage_v5/webapp_react/src/components/Core.tsx.md`
- `src/vantage_v5/webapp_react/src/components/Surfaces.tsx.md`
- `src/vantage_v5/webapp_react/src/main.tsx.md`
- `src/vantage_v5/webapp_react/src/normalizers.ts.md`
- `src/vantage_v5/webapp_react/src/visibleArtifacts.ts.md`
- `src/vantage_v5/webapp_react/src/styles.css.md`

## Current Frontend Shape

- `Chat` stays the default surface.
- `Whiteboard` is a separate drafting surface that becomes visually primary when opened.
- `Whiteboard` now keeps source editing and rendered preview distinct, so math-capable rendering stays on the preview/read side rather than inside the textarea itself.
- `Vantage` is the inspection surface. Its visible docks currently focus on:
  - an answer dock for Working Memory framing, Reasoning Path, Recall, Memory Trace, Learned, and semantic understanding
  - a separate Scenario Lab dock
- The Library dock remains in the DOM/data model with Concept KB, Memories, Artifacts, Reference Notes, pinned-context controls, and an inspector, but it is temporarily hidden from the visible Vantage surface while the product stays simpler.
- `Recall` is the surfaced retrieved subset shown in Vantage and compact chat evidence.
- `Working Memory` is the broader inspection frame for what was in scope for generation. The React Vantage view now consumes the bounded `working_memory_view` response contract to show role-grouped context, provenance, and execution/write summaries without exposing hidden chain-of-thought or full resource bodies.
- `Memory Trace` is exposed in Vantage as recent-history contribution and the created turn trace record, not as a fourth top-level product surface or a Library bucket.
- `Semantic Frame` / `Semantic Policy` payloads are normalized client-side and surfaced as compact `Understood As` / `Next Step` cues rather than a new diagnostics panel.
- React state now separates the current foreground view from explicit visible surfaces, the active whiteboard editor buffer, selected-resource metadata, pinned context, and included request context. Legacy component props still receive compatible `view`, `workspace`, `activeSurfaceId`, and `surfacePayloads` fields while the reducer keeps the clearer domains in sync.
- The auth gate can switch between sign-in and create-account modes when account creation is enabled, with the create path posting to `/api/accounts` and then entering the same authenticated shell.
- The authenticated masthead includes a compact `API key` control that opens the provider-key dialog and mirrors `/api/openai-key` masked status, save, and clear behavior.
- The React shell now includes PWA metadata and a root service worker so a Cloudflare-protected Vantage v6 deployment can be installed from iPhone Safari. The service worker caches only public generated assets and icons, never `/api/*` user data.
- The generated React production bundle under `src/vantage_v5/webapp/generated/` is the only product frontend served by FastAPI. If it is missing, `/` returns a clear build-required error rather than falling back to a legacy shell.

## Webapp Tests

- [src/vantage_v5/webapp_react/src/App.test.tsx.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp_react/src/App.test.tsx.md)
- [src/vantage_v5/webapp_react/src/entrypoints.test.ts.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp_react/src/entrypoints.test.ts.md)
- [src/vantage_v5/webapp_react/src/appReducer.test.ts.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp_react/src/appReducer.test.ts.md)
- [src/vantage_v5/webapp_react/src/inspectionModel.test.ts.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp_react/src/inspectionModel.test.ts.md)
- [src/vantage_v5/webapp_react/src/visibleArtifacts.test.ts.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp_react/src/visibleArtifacts.test.ts.md)
