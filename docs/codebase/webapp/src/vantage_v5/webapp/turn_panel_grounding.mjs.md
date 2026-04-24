# `src/vantage_v5/webapp/turn_panel_grounding.mjs`

Tiny render-copy helper for the Vantage turn panel and answer dock.

## Purpose

- Keep the panel label text testable without importing the DOM-bound browser entrypoint.
- Produce one small grounding copy object for the turn meta, dock label, and turn intent label.

## Key Behavior

- `buildTurnPanelGroundingCopy()` preserves the current product wording for the six grounding cases plus the idle and learned-only fallback branches.
- Recall-grounded turns show as `Recall` in the dock while broader grounded modes keep their own labels.
- `pending_whiteboard` is surfaced as `Prior Whiteboard`.
- `mixed_context` keeps the combined source label, such as `Recall + Recent Chat`.
- Learned counts use `What I learned` wording in the dock meta so the answer-dock summary matches the rest of the provenance surface.
- The helper does not render Reasoning Path or Memory Trace details itself; it only keeps the answer-dock labels and meta copy consistent across render paths and tests.
