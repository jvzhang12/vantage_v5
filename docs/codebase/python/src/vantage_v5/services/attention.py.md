# `src/vantage_v5/services/attention.py`

Implements the first-pass Attention + Navigator selection layer for Vantage.

## Purpose

- Turn each user request into a structured `QueryFrame`.
- Build deterministic `AttentionResource` entries for visible artifacts, workspaces, saved artifacts, memories, concepts, protocols, memory traces, calendar, and tasks.
- Rank compact `AttentionCandidate` records before the Navigator LLM chooses which resources should actually enter the workspace/context.
- Combine deterministic key/time/app ranking with a local semantic vector similarity signal so retrieval can catch close paraphrases without giving up product control.
- Provide a conservative deterministic fallback when the Navigator is unavailable.

## Core Data Flow

- `build_query_frame()` extracts domains, operation hints, entities, requested artifact kinds, and temporal references such as today, tomorrow, last week, or last Tuesday.
- `AttentionEngine.prepare_turn()` indexes candidate resources from the current runtime and user-scoped operational providers.
- Ranking favors visible artifacts first, then exact key/entity matches, temporal matches, operational app matches, and recency.
- Hybrid ranking adds `retrieval_scores` to each candidate, including deterministic score, temporal score, semantic vector similarity, vector bonus, and final hybrid score.
- `AttentionTurn.select()` normalizes the Navigator's selection or chooses a small deterministic fallback set.
- `attention_payload()` exposes `query_frame`, `attention_candidates`, `navigator_selection`, and `selected_attention_resources` for `/api/chat`, `system_state`, and the Vantage receipt.
- `apply_attention_surface_selection()` lets Navigator-selected operational resources foreground surfaces such as calendar day, calendar week, task focus, or whiteboard.

## Important Boundaries

- Candidate payloads stay compact and do not carry full bodies.
- Full resource values load only after Navigator selection.
- Selected attention resources are separate from `visible_artifacts` for response grounding, but the server may convert them into visible-artifact-shaped context for the mutation compiler.
- No embeddings or vector database are used in this slice.
