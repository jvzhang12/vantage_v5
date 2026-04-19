# Webapp Codebase Summaries

This directory mirrors the web client under `src/vantage_v5/webapp` plus the browser-facing `.test.mjs` files under `tests/`.

The goal is the same as the Python summaries: let future agents understand the shipped client surfaces, state model, payload contract, and focused browser-side tests without reverse-engineering `app.js` from scratch.

## Suggested Reading Order

1. [src/vantage_v5/webapp/index.html.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/index.html.md)
2. [src/vantage_v5/webapp/app.js.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/app.js.md)
3. [src/vantage_v5/webapp/product_identity.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/product_identity.mjs.md)
4. [src/vantage_v5/webapp/turn_payloads.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/turn_payloads.mjs.md)
5. The smaller helper modules listed below
6. The focused test summaries that cover the behavior you plan to touch

## Entry Surface

- [src/vantage_v5/webapp/index.html.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/index.html.md)
- [src/vantage_v5/webapp/styles.css.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/styles.css.md)
- [src/vantage_v5/webapp/app.js.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/app.js.md)

## State And Helper Modules

- [src/vantage_v5/webapp/chat_request.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/chat_request.mjs.md)
- [src/vantage_v5/webapp/product_identity.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/product_identity.mjs.md)
- [src/vantage_v5/webapp/surface_state.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/surface_state.mjs.md)
- [src/vantage_v5/webapp/turn_panel_grounding.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/turn_panel_grounding.mjs.md)
- [src/vantage_v5/webapp/turn_payloads.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/turn_payloads.mjs.md)
- [src/vantage_v5/webapp/whiteboard_decisions.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/whiteboard_decisions.mjs.md)
- [src/vantage_v5/webapp/workspace_state.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/src/vantage_v5/webapp/workspace_state.mjs.md)

## Current Frontend Shape

- `Chat` stays the default surface.
- `Whiteboard` is a separate drafting surface that becomes visually primary when opened.
- `Vantage` is the inspection surface with three docks:
  - an answer dock for Working Memory framing, Reasoning Path, Recall, Memory Trace, and Learned
  - a separate Scenario Lab dock
  - a Library dock with Concept KB, Memories, Artifacts, Reference Notes, and an inspector
- `Recall` is the surfaced retrieved subset shown in Vantage and compact chat evidence.
- `Working Memory` is the broader inspection frame for what was in scope for generation.
- `Memory Trace` is exposed in Vantage as recent-history contribution and the created turn trace record, not as a fourth top-level product surface or a Library bucket.

## Webapp Tests

- [tests/product_identity.test.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/tests/product_identity.test.mjs.md)
- [tests/webapp_state_model.test.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/tests/webapp_state_model.test.mjs.md)
- [tests/webapp_whiteboard_decisions.test.mjs.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/tests/webapp_whiteboard_decisions.test.mjs.md)
