# `src/vantage_v5/services/attention.py`

Implements the first-pass Attention + Navigator selection layer for Vantage.

## Purpose

- Turn each user request into a structured `QueryFrame`.
- Build deterministic `AttentionResource` entries for visible artifacts, workspaces, saved artifacts, memories, concepts, protocols, memory traces, calendar, and tasks, with explicit product scope/provenance metadata.
- Rank compact `AttentionCandidate` records before the Navigator LLM chooses which resources should actually enter the workspace/context.
- Combine deterministic key/time/app ranking with a local semantic vector similarity signal so retrieval can catch close paraphrases without giving up product control.
- Provide a conservative deterministic fallback when the Navigator is unavailable.

## Core Data Flow

- `build_query_frame()` extracts domains, operation hints, entities, requested artifact kinds, and temporal references such as today, tomorrow, last week, or last Tuesday.
- `AttentionEngine.prepare_turn()` indexes candidate resources from the current runtime and user-scoped operational providers.
- Ranking favors visible artifacts first, then exact key/entity matches, temporal matches, operational app matches, and recency. Broad saved-material lookups also give a small penalty to derivative action/step artifacts when their source artifact is present, while explicit first-action/next-step queries can still choose the derivative.
- Hybrid ranking adds `retrieval_scores` to each candidate, including deterministic score, temporal score, semantic vector similarity, vector bonus, and final hybrid score.
- `AttentionTurn.select()` normalizes the Navigator's selection or chooses a small deterministic fallback set. Selection normalization accepts either public resource ids or compact candidate ids, and when a same-title opened copy and its source artifact are both selected it makes the source artifact the primary open target.
- `attention_payload()` exposes `query_frame`, `attention_candidates`, `navigator_selection`, and `selected_attention_resources` for `/api/chat`, `system_state`, and the Vantage receipt. Candidate and selected-resource DTOs now carry `scope`, `durability`, and `is_canonical` directly rather than requiring consumers to infer product provenance from `source_status.store`.
- `apply_attention_surface_selection()` lets Navigator-selected resources foreground surfaces such as calendar day, calendar week, task focus, or whiteboard. Selecting a saved artifact for Whiteboard is treated as an `open_only` UI action, not as draft/write intent, and it can override an already-visible operational surface such as Today.

## Important Boundaries

- Candidate payloads stay compact and do not carry full bodies.
- Full resource values load only after Navigator selection.
- Selected attention resources are separate from `visible_artifacts` for response grounding, but the server may convert them into visible-artifact-shaped context for the mutation compiler.
- No embeddings or vector database are used in this slice.
- Scope metadata is payload-only and does not affect candidate ranking or Navigator fallback selection.
