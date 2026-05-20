# Frontend Legacy Retirement Audit

Date: 2026-05-20

## Scope

This audit covers browser-facing frontend entrypoints, generated/static bundle paths, server static routes, package scripts, tests, and documentation references. It intentionally does not change backend payloads, TurnPlan, Attention/Recall, routing, retrieval, or write paths.

## Active React Path

- Source root: `src/vantage_v5/webapp_react/`
- Dev HTML: `src/vantage_v5/webapp_react/index.html`
- React mount: `src/vantage_v5/webapp_react/src/main.tsx` mounts `App` into `#root` and registers `/sw.js` when the browser context is secure.
- App shell and behavior: `src/vantage_v5/webapp_react/src/App.tsx`, reducer/state modules, components, normalizers, and focused Vitest tests under the same tree.
- Build config: `vite.config.ts`
  - `root: "src/vantage_v5/webapp_react"`
  - `base: "/static/generated/"`
  - `build.outDir: "../webapp/generated"`
  - production entry emitted as `assets/app.js`
- Runtime generated bundle path: `src/vantage_v5/webapp/generated/`, ignored by git and recreated by `npm run build`.

## Server Serving Paths

- `src/vantage_v5/server.py` mounts `src/vantage_v5/webapp` at `/static`.
- `GET /` serves `src/vantage_v5/webapp/generated/index.html` when that file exists.
- `GET /` falls back to `src/vantage_v5/webapp/index.html` when the generated React build is absent.
- Root PWA routes `GET /manifest.webmanifest`, `GET /sw.js`, and `GET /icons/{filename}` prefer generated assets under `src/vantage_v5/webapp/generated/` and fall back to `src/vantage_v5/webapp_react/public/`.
- Auth middleware keeps `/`, `/static/*`, root PWA assets, and icons public so the shell can render before login while `/api/*` stays protected where configured.

## Generated And Static Bundle Paths

- Active generated React build output after `npm run build`:
  - `src/vantage_v5/webapp/generated/index.html`
  - `src/vantage_v5/webapp/generated/assets/app.js`
  - `src/vantage_v5/webapp/generated/assets/index.css`
  - `src/vantage_v5/webapp/generated/manifest.webmanifest`
  - `src/vantage_v5/webapp/generated/sw.js`
  - `src/vantage_v5/webapp/generated/icons/*`
- These files are ignored by `.gitignore`, so they are not a committed source of truth.
- Legacy/static shell files still committed under `src/vantage_v5/webapp/`:
  - `index.html`
  - `app.js`
  - `styles.css`
  - helper modules such as `auth_state.mjs`, `chat_request.mjs`, `math_render.mjs`, `product_identity.mjs`, `surface_state.mjs`, `turn_panel_grounding.mjs`, `turn_payloads.mjs`, `whiteboard_decisions.mjs`, and `workspace_state.mjs`
  - vendored local browser libraries under `vendor/`

## Package Scripts And Tests

- `npm run dev` runs Vite against the React source root on `127.0.0.1:5173`.
- `npm run build` emits the React production bundle into `src/vantage_v5/webapp/generated/`.
- `npm run typecheck` typechecks the React/TypeScript source.
- `npm test` runs Vitest. Current React coverage includes `App.test.tsx`, reducer tests, inspection model tests, visible artifact tests, and `entrypoints.test.ts`.
- Legacy helper tests still import committed static modules under `src/vantage_v5/webapp/`, especially `tests/product_identity.test.mjs`, `tests/math_render.test.mjs`, `tests/webapp_state_model.test.mjs`, `tests/webapp_whiteboard_decisions.test.mjs`, and `tests/webapp_draft_status.test.mjs`.
- `tests/test_server.py` covers HTTP static/PWA routes, generated React shell precedence, legacy shell fallback, and auth behavior around public shell assets.

## Documentation References

- Current docs already recognize the React migration and generated build in:
  - `README.md`
  - `docs/architecture-overview.md`
  - `docs/codebase/webapp/README.md`
  - `docs/vantage-codebase-functionality-map.md`
  - React mirrored summaries under `docs/codebase/webapp/src/vantage_v5/webapp_react/`
  - `docs/vantage-capability-interface-map.md`
- UI research and archived implementation-plan documents still describe historical vanilla webapp slices, but they are not current frontend serving contracts.

## Active Versus Legacy Assessment

Active:

- React source under `src/vantage_v5/webapp_react/`
- Generated React bundle under `src/vantage_v5/webapp/generated/` after `npm run build`
- Server root route when generated `index.html` exists
- Root PWA asset routes and generated/public PWA files

Still active as support or test fixtures:

- `src/vantage_v5/webapp/generated/` path as the server-served production bundle location
- `src/vantage_v5/webapp_react/public/` as the fallback source for root PWA assets
- Legacy helper modules while Node tests still import them directly
- Legacy `index.html`, `app.js`, and `styles.css` as server fallback when no generated React build exists

Suspected legacy, not safe to delete in this slice:

- `src/vantage_v5/webapp/index.html`
- `src/vantage_v5/webapp/app.js`
- `src/vantage_v5/webapp/styles.css`
- Legacy helper modules in `src/vantage_v5/webapp/*.mjs`
- `src/vantage_v5/webapp/vendor/*`

## Evidence Collected

- Source inspection confirms Vite points at the React tree and outputs to `/static/generated/`.
- Source inspection confirms FastAPI serves generated React `index.html` first and falls back to the legacy static shell.
- Focused server-route tests confirm `GET /` serves generated React HTML with `/static/generated/assets/app.js` and `/static/generated/assets/index.css` when `generated/index.html` exists.
- Focused server-route tests confirm `GET /` currently falls back to the legacy `src/vantage_v5/webapp/index.html` shell when `generated/index.html` is absent.
- Focused server-route tests confirm root PWA routes prefer generated manifest, service worker, and icon files over React public fallbacks when generated files exist.
- `git check-ignore` confirms `src/vantage_v5/webapp/generated/` is ignored build output.
- `npm run build` confirms the generated React bundle is recreated in the expected server-served directory.
- Browser smoke against the Vite dev server confirms the React shell loads from `http://127.0.0.1:5173/static/generated/`.
- Browser smoke against the FastAPI server after `npm run build` confirms `/` serves generated React HTML that references `/static/generated/assets/app.js`.
- Focused Vitest coverage now asserts the React entrypoint and generated bundle contract.

## Risks

- A clean checkout without a generated build still relies on the legacy fallback for `GET /`.
- Several tests still import legacy helper modules directly, so deleting `src/vantage_v5/webapp/*.mjs` would break test coverage before equivalent React/TypeScript coverage exists.
- Some older docs and UI research plans still name `app.js`, `index.html`, and `styles.css`; many are historical and should not be mass-edited without separating active docs from archive.
- The server still mounts all of `src/vantage_v5/webapp` at `/static`, so any legacy file in that tree remains browser-reachable until routes or file layout change.

## Proposed Removal Slices

1. Build-contract hardening:
   - Keep the React entrypoint and server-route tests.
   - Decide whether CI should run `npm run build` before server-route smoke tests.

2. Test migration:
   - Move legacy helper coverage that still matters into React/TypeScript modules or declare those helpers intentionally retained.
   - Retire tests that only assert legacy HTML/cache-busting behavior once server fallback is no longer product-supported.

3. Docs cleanup:
   - Keep active docs aligned with the React/generated serving contract.
   - Leave archived UI research and implementation plans unchanged unless they claim to be current.

4. Fallback policy decision:
   - If clean checkouts must serve a shell without running `npm run build`, keep a minimal committed fallback or add an explicit setup failure page.
   - If generated React becomes mandatory, remove the legacy fallback branch from `GET /` in a backend-static route slice with focused route tests.

5. Code deletion:
   - Delete legacy `index.html`, `app.js`, `styles.css`, helper modules, and vendor files only after route tests, migrated frontend tests, and docs prove no active consumer remains.

## Deletion Status

No deletion happened in this slice.
