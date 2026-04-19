# `src/vantage_v5/webapp/styles.css`

Single-file visual system for the Vantage frontend.

## Purpose

- Define the warm paper-like visual theme for chat, whiteboard, and `Vantage`.
- Control the shell layout for normal chat, whiteboard-focused drafting, and `Vantage` inspection.
- Style notices, badges, panels, library cards, compact chat result cards, and the whiteboard editor.
- Give Scenario Lab a distinct comparison-first treatment so it reads as separate from the working-memory influence view.

## Notable Behavior

- Uses `.shell--whiteboard` to make the whiteboard the main canvas with chat as a sidebar.
- Uses `.shell--vantage` to present chat and guided inspection side-by-side.
- Treats the whiteboard, `Vantage`, and chat as distinct surfaces rather than collapsing them into one stacked layout.
- Styles the `Reasoning Path` rail as clickable disclosure cards so the user can open turn-scoped detail without leaving the Vantage answer dock.
- Uses Scenario Lab-specific dock, overview-grid, branch-card, and transcript-card styling to distinguish durable scenario review from ordinary memory inspection.
