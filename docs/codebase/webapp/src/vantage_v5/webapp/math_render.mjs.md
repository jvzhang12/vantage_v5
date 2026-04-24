# `src/vantage_v5/webapp/math_render.mjs`

Shared frontend renderer for rich read surfaces that need plain text, inline math, inline code, block math, and fenced code blocks.

## Purpose

- Tokenize read-surface text into plain-text, inline-math, inline-code, block-math, and fenced-code tokens without re-parsing in each caller.
- Render the same source text into chat bodies, library cards, library inspection bodies, and the whiteboard preview.
- Keep the whiteboard editor itself as raw source while the preview surface shows the rendered result.

## Key Functions

- `tokenizeMathText()`
- `deriveWhiteboardPreviewState()`
- `hasMathSyntax()`
- `hasCodeSyntax()`
- `renderRichText()`

## Notable Behavior

- Treats `\$` as a literal dollar sign in text instead of math syntax.
- Treats inline backticks as code spans and keeps fenced code readable with a small language/meta header when one is present.
- Uses the local vendored KaTeX and Highlight.js runtimes when available, but falls back safely to plain text so the app still boots if the assets are absent.
- Supports both `$...$` inline math and `$$...$$` block math, plus `\(...\)` and `\[...\]` delimiters.
- Leaves fenced code blocks opaque to the math parser instead of trying to render math inside them.
- Returns a DOM fragment-like rendered structure through the supplied container, so the caller stays in control of the surface it is populating.
- Exposes one shared whiteboard-preview gate (`deriveWhiteboardPreviewState()`) so the app can keep ordinary prose drafts quiet while reliably showing the preview for math, code, or mixed drafts.
