# `tests/math_render.test.mjs`

Focused unit tests for the shared math-render parser and DOM render path.

## Purpose

- Verify prose, inline math, and inline code tokenization.
- Verify block math tokenization.
- Verify escaped dollar handling stays literal.
- Verify fenced code blocks stay opaque to the math parser while still surfacing lightweight language cues.
- Verify the helper’s math-syntax and code-syntax detection stay narrow and deterministic.
- Verify the shared preview gate only becomes visible for math/code drafts and stays hidden for ordinary prose.
- Verify the shared `renderRichText()` DOM path produces the expected text, KaTeX node, inline code span, and fenced-code structure without needing the full app shell.

## Why It Matters

- This is the main guardrail against regressions in the shared read-surface renderer, especially because chat, concept cards, the inspector, and the whiteboard preview now all consume the same parsing path.
