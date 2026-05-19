# `src/vantage_v5/webapp_react/src/components/Inspection.tsx`

React implementation of the Vantage Working Memory / “Why this answer?” view.

## Purpose

- Render a premium latest-turn answer receipt from normalized backend provenance and the public `working_memory_view` contract.
- Keep Vantage/Inspect focused on the latest answer rather than chat history or dashboards.

## Coverage

- Empty state, loading skeleton component, summary strip, Working Memory role sections, Context Used, Artifacts & Surfaces, Decision Path, and Memory / Actions / Writes sections.
- The Working Memory panel groups compact resources by Answer Context, Recall Context, Protocol Guidance, Surface To Open, and Pinned / Continuity Context, plus a bounded execution/write summary.
- The panel shows grounding/provenance evidence and execution context only; it does not display hidden chain-of-thought, raw prompts, or full resource bodies.
- Back-to-chat behavior for the Vantage top-button flow.
