# `src/vantage_v5/webapp_react/public/sw.js`

Root-scoped service worker for the Vantage v6 PWA shell.

## Purpose

- Let Safari/Chromium treat the hosted Vantage site as an installable app.
- Cache only public generated frontend assets and icons.

## Notable Behavior

- Ignores every `/api/*` request so chat, auth, whiteboard, memory, and artifact payloads are never service-worker cached.
- Uses a versioned cache and deletes older Vantage static caches on activation.
