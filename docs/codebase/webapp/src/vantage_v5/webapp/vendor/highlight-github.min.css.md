# `src/vantage_v5/webapp/vendor/highlight-github.min.css`

Vendored Highlight.js theme used for local fenced-code readability.

## Purpose

- Provide a local syntax-highlighting theme for the vendored Highlight.js runtime.
- Keep fenced code visually legible in the shared read-surface renderer without depending on a runtime CDN stylesheet.

## Notable Behavior

- This file is third-party vendored code rather than repo-authored application logic.
- The app treats the theme as a presentation dependency for `math_render.mjs` and the rendered whiteboard/chat/library read surfaces.
