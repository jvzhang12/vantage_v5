# `src/vantage_v5/webapp_react/src/entrypoints.test.ts`

Vitest coverage for the React frontend entrypoint and generated bundle contract.

## Purpose

- Verify Vite still uses `src/vantage_v5/webapp_react` as the React source root.
- Verify production builds still emit to `src/vantage_v5/webapp/generated/` with `/static/generated/` public URLs.
- Verify the source React HTML mounts into `#root` through `/src/main.tsx` instead of the legacy `/static/app.js` and `/static/styles.css` entrypoints.

## Why It Matters

- These assertions support legacy/static frontend retirement work by making the active React entry path explicit before legacy files are removed.
