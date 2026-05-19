# Webapp Codebase Summaries

This directory mirrors the legacy web client under `src/vantage_v5/webapp`, the React migration under `src/vantage_v5/webapp_react`, plus the browser-facing frontend tests.

The goal is the same as the Python summaries: let future agents understand the shipped client surfaces, state model, payload contract, and focused browser-side tests without reverse-engineering `app.js` from scratch.

## Suggested Reading Order

1. `src/vantage_v5/webapp_react/src/App.tsx.md`
2. `src/vantage_v5/webapp_react/src/components/Core.tsx.md`
3. `src/vantage_v5/webapp_react/src/components/Surfaces.tsx.md`
4. `src/vantage_v5/webapp_react/src/normalizers.ts.md`
5. Legacy `src/vantage_v5/webapp/app.js.md` and helper summaries when comparing parity

## React Migration Surface

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

## Legacy Entry Surface

- [src/vantage_v5/webapp/index.html.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/index.html.md)
- [src/vantage_v5/webapp/styles.css.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/styles.css.md)
- [src/vantage_v5/webapp/app.js.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/app.js.md)

## State And Helper Modules

- [src/vantage_v5/webapp/chat_request.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/chat_request.mjs.md)
- [src/vantage_v5/webapp/auth_state.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/auth_state.mjs.md)
- [src/vantage_v5/webapp/math_render.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/math_render.mjs.md)
- [src/vantage_v5/webapp/product_identity.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/product_identity.mjs.md)
- [src/vantage_v5/webapp/surface_state.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/surface_state.mjs.md)
- [src/vantage_v5/webapp/turn_panel_grounding.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/turn_panel_grounding.mjs.md)
- [src/vantage_v5/webapp/turn_payloads.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/turn_payloads.mjs.md)
- [src/vantage_v5/webapp/vendor/katex.min.js.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/vendor/katex.min.js.md)
- [src/vantage_v5/webapp/whiteboard_decisions.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/whiteboard_decisions.mjs.md)
- [src/vantage_v5/webapp/workspace_state.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/workspace_state.mjs.md)

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
- The auth gate can switch between sign-in and create-account modes when account creation is enabled, with the create path posting to `/api/accounts` and then entering the same authenticated shell.
- The authenticated masthead includes a compact `API key` control that opens the provider-key dialog and mirrors `/api/openai-key` masked status, save, and clear behavior.
- The React shell now includes PWA metadata and a root service worker so a Cloudflare-protected Vantage v6 deployment can be installed from iPhone Safari. The service worker caches only public generated assets and icons, never `/api/*` user data.

## Webapp Tests

- [src/vantage_v5/webapp_react/src/App.test.tsx.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp_react/src/App.test.tsx.md)
- [tests/product_identity.test.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/tests/product_identity.test.mjs.md)
- [tests/math_render.test.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/tests/math_render.test.mjs.md)
- [tests/webapp_state_model.test.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/tests/webapp_state_model.test.mjs.md)
- [tests/webapp_whiteboard_decisions.test.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/tests/webapp_whiteboard_decisions.test.mjs.md)
