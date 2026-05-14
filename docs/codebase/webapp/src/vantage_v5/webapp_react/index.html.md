# `src/vantage_v5/webapp_react/index.html`

Vite entry HTML for the React frontend.

## Purpose

- Provides the `#root` mount point for the React app.
- Loads `src/main.tsx` during Vite development and production builds.
- Declares the root PWA manifest, iOS home-screen metadata, Apple touch icon, theme color, and app description used when Vantage v6 is installed from Safari.

## Notes

- The built version is emitted under `src/vantage_v5/webapp/generated/` and served by FastAPI when present.
