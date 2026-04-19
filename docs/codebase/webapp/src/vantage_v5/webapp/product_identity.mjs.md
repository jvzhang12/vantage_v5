# `src/vantage_v5/webapp/product_identity.mjs`

Presentation helpers for the small “this product is different” signals shown directly in chat and in guided inspection.

## Purpose

- Build compact per-turn evidence chips such as recalled-item counts, learned items, Scenario Lab identity, and product-specific grounding labels like Recall, Whiteboard, Prior Whiteboard, or Recall + Recent Chat.
- Build the short Vantage header summary that mirrors the same turn truth without conflating Recall with broader Working Memory framing or other grounded context such as Whiteboard or Recent Chat.
- Build the staged `Reasoning Path` inspection model for the answer dock: Request, Route, Candidate context, Recall, Working Memory, and Outcome, including stage metadata and drill-down groups.
- Build the short Memory Trace inspection copy that explains whether recent history contributed to Recall and whether the turn created a durable or experiment-scoped trace record.
- Normalize whiteboard lifecycle labels such as transient draft, saved whiteboard, and promoted artifact.

## Key Functions

- `buildChatTurnEvidence()`
- `buildGuidedInspectionSummary()`
- `buildReasoningPathInspection()`
- `buildMemoryTraceSummary()`
- `describeResponseModeLabel()`
- `deriveTurnGrounding()`
- `deriveWhiteboardLifecycle()`

## Notable Behavior

- Prefers short product-facing labels over raw internal payload names.
- Reads the canonical backend truth from `kind`, `groundingMode`, and recall counts instead of depending on synthetic client-only grounding kinds.
- Reuses the shared turn-payload helpers for learned-item fallback and canonical recall counts, so compact evidence chips do not depend on their own parallel `created_record` or camelCase/snake_case parsing.
- Centralizes the turn-grounding view-model the app uses for Vantage summaries and panels, including the canonical `recallCount` even when the visible recalled-item list is shorter.
- Uses the same canonical recall count for compact chat evidence, so chat chips and Vantage do not disagree when the visible recalled-item list is shorter than the grounded count.
- Translates response-mode payloads into user-facing badges like `Best Guess`, `Recall`, `Whiteboard`, `Prior Whiteboard`, source-specific mixed-context labels such as `Recall + Recent Chat`, or `Used 2 recalled items`.
- Keeps `Memory Trace` out of response-mode grounding labels. Recent history contributes to the UI as a recall source and a trace-record summary, not as a separate top-level grounding mode.
- Keeps the `Reasoning Path` rail grounded in the existing request, interpretation, candidate context, recall, working-memory, and outcome payloads instead of inventing a separate backend trace shape.
- Keeps Scenario Lab `Best Guess` turns explicitly marked in chat evidence and guided inspection instead of suppressing the ungrounded state behind branch-count badges.
- Keeps Scenario Lab fallback turns visibly marked in chat so they still read as a routed reasoning mode rather than ordinary chat.
- Keeps the Vantage summary aligned with the same truth used for chat chips, including Scenario Lab branch counts and library context.
- Uses product-facing grounding labels even when the backend still reports machine-facing mixed-context modes, so the compact chat and Vantage surfaces explain what actually supported the answer.
- Keeps `Reasoning Path` truthful to the repository’s current contract by summarizing full Working Memory as “what was in scope for this answer,” while leaving the narrower recalled-item list visible separately as `Recall`. The Working Memory drill-down is a scope table, so the user can see which inputs were included or excluded for generation. Candidate `memory_trace` items stay in `Candidate context`, while recalled recent-history items contribute to the Memory Trace summary and the scope table.
- Exposes the concrete candidate pools and selected recall items in the stage drill-down so users can inspect what was actually pulled up without opening chat internals, including recent-history candidates from `candidate_trace_notes`.
- Carries requested whiteboard mode, resolved whiteboard mode, decision source, and selected-record continuity reason into the path summary so the interpretation stage can explain route choices without exposing raw chain-of-thought text.
