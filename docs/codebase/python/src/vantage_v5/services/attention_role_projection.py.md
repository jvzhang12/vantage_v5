# `src/vantage_v5/services/attention_role_projection.py`

Helpers for projecting finalized `/api/chat` context into product-safe Attention/Recall and Working Memory roles.

## Purpose

- Build `final_response.attention_recall_role_projection` for JSON traces without changing execution.
- Build the public latest-turn `/api/chat` `working_memory_view` contract from the same role projection plus compact TurnPlan execution/write summaries.
- Group finalized selected Attention resources, visible context, pinned context, surface-open targets, and legacy Recall/`working_memory` records into compact role views.
- Make the future Vantage Working Memory model inspectable: Attention is the broad turn selection layer, Recall is the memory-grounding role over that selection, and Working Memory is all selected or in-scope context.
- Consume the internal `AttentionRecallContextHandoff` read model as the source for role projection and Working Memory view construction.

## Key Functions

- `build_attention_recall_role_projection()`: builds the internal context handoff from finalized request/response dictionaries and returns the compatibility trace payload.
- `build_working_memory_view_payload()`: consumes finalized request/response dictionaries plus an optional context handoff, role projection, and TurnPlan trace payload, then returns the bounded public Working Memory view.

## Notable Behavior

- Roles include `answer_context`, `recall_context`, `surface_to_open`, `protocol_guidance`, and `pinned_or_continuity_context`.
- Resource entries include ids, kind/type, title/label, roles, provenance, selected/visible/pinned flags, compact summary/excerpt fields, and a best-effort `sent_to_response_llm` marker.
- The underlying context handoff compares selected Attention ids with legacy Recall ids so trace readers can see overlap and gaps while `ChatService.search_context()` remains unchanged.
- Excerpts are bounded and intended for provenance/debugging only; this module does not expose hidden model reasoning or full artifact bodies.
- `working_memory_view` is public by default in `/api/chat`, but it stays compact: resources carry ids, titles, roles, origins, flags, provenance, short excerpts, LLM-sent markers, and influence flags; execution summary carries surface mode plus write/proposal categories rather than full created content.
