# Frontend Legacy Retirement Note

> Status: Historical rationale
> Current source of truth: [architecture-overview.md](architecture-overview.md), [deployment.md](deployment.md), and [codebase/webapp/README.md](codebase/webapp/README.md)
> Note: This note records the completed retirement of the old vanilla/static frontend path. React source plus generated React build output are the only product frontend path.

Date: 2026-05-20

## Scope

This note records the retirement of the committed vanilla/static frontend entrypoints. The slice changed only frontend static serving, tests, and documentation. It did not change backend payloads, TurnPlan, Attention/Recall, routing semantics, retrieval, write paths, or chat behavior.

## Active Frontend Path

- Source root: `src/vantage_v5/webapp_react/`
- Dev HTML: `src/vantage_v5/webapp_react/index.html`
- React mount: `src/vantage_v5/webapp_react/src/main.tsx` mounts `App` into `#root` and registers `/sw.js` when the browser context is secure.
- App shell and behavior: `src/vantage_v5/webapp_react/src/App.tsx`, reducer/state modules, components, normalizers, visible-artifact helpers, and focused Vitest tests under the same tree.
- Build config: `vite.config.ts`
  - `root: "src/vantage_v5/webapp_react"`
  - `base: "/static/generated/"`
  - `build.outDir: "../webapp/generated"`
  - production entry emitted as `assets/app.js`
- Runtime generated bundle path: `src/vantage_v5/webapp/generated/`, ignored by git and recreated by `npm run build`.

## Server Serving Contract

- `src/vantage_v5/server.py` mounts `src/vantage_v5/webapp` at `/static` so ignored generated assets are served at `/static/generated/...`.
- `GET /` serves `src/vantage_v5/webapp/generated/index.html` when that file exists.
- If `src/vantage_v5/webapp/generated/index.html` is missing, `GET /` returns a clear `503` setup/build error explaining that the generated React frontend build is missing and `npm run build` is required.
- There is no legacy product frontend fallback.
- Root PWA routes `GET /manifest.webmanifest`, `GET /sw.js`, and `GET /icons/{filename}` prefer generated assets under `src/vantage_v5/webapp/generated/` and fall back to `src/vantage_v5/webapp_react/public/`.
- Auth middleware keeps `/`, `/static/*`, root PWA assets, and icons public so the shell can render before login while `/api/*` stays protected where configured.

## Retired Files

The committed legacy files under `src/vantage_v5/webapp/` were removed:

- `index.html`
- `app.js`
- `styles.css`
- `auth_state.mjs`
- `chat_request.mjs`
- `math_render.mjs`
- `product_identity.mjs`
- `surface_state.mjs`
- `turn_panel_grounding.mjs`
- `turn_payloads.mjs`
- `whiteboard_decisions.mjs`
- `workspace_state.mjs`
- `vendor/highlight-github.min.css`
- `vendor/highlight.min.js`
- `vendor/katex.min.js`

The ignored `src/vantage_v5/webapp/generated/` build output directory remains the runtime static asset location.

## Tests

- `tests/test_server.py` covers generated React shell precedence, `/static/generated/` asset serving, missing-build `503` behavior, generated/public PWA asset serving, and auth behavior around public shell assets.
- React/Vitest coverage remains under `src/vantage_v5/webapp_react/src/`, including `App.test.tsx`, reducer tests, inspection model tests, visible artifact tests, and `entrypoints.test.ts`.
- Direct Node tests for removed legacy helper modules were removed with those modules:
  - `tests/product_identity.test.mjs`
  - `tests/math_render.test.mjs`
  - `tests/webapp_state_model.test.mjs`
  - `tests/webapp_whiteboard_decisions.test.mjs`
  - `tests/webapp_draft_status.test.mjs`

## Evidence

- Vite points at the React tree and outputs to `/static/generated/`.
- Server-route tests confirm `GET /` serves generated React HTML with `/static/generated/assets/app.js` and `/static/generated/assets/index.css` when `generated/index.html` exists.
- Server-route tests confirm `GET /` returns the explicit build-required error when `generated/index.html` is absent.
- Server-route tests confirm root PWA routes prefer generated manifest, service worker, and icon files over React public fallbacks when generated files exist.
- `git check-ignore` confirms `src/vantage_v5/webapp/generated/` is ignored build output.
- `npm run build` recreates the generated React bundle in the expected server-served directory.

## Remaining Notes

- Active docs now describe React/generated as the only product frontend path.
- UI research and archived implementation-plan documents may still discuss historical vanilla webapp slices; they are not current serving contracts.
- A clean checkout must run `npm run build` before using the FastAPI-served browser shell.

## Deletion Status

Legacy committed static frontend files and their direct legacy-helper tests were deleted in this retirement slice.
