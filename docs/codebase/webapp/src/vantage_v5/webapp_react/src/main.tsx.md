# `src/vantage_v5/webapp_react/src/main.tsx`

React browser entrypoint.

## Purpose

- Mounts the React `App` into the Vite root element.
- Imports the Tailwind/Vantage stylesheet.
- Registers the root service worker on HTTPS, localhost, or 127.0.0.1 so the hosted Vantage v6 site can behave as an installable PWA.

## Notes

- Kept intentionally small so app behavior remains inside typed React modules; service-worker registration is silent if unavailable or blocked.
