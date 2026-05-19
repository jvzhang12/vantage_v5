# `src/vantage_v5/services/attention_role_projection.py`

Trace-only observability helpers for projecting finalized `/api/chat` context into product roles.

## Purpose

- Build `final_response.attention_recall_role_projection` for JSON traces without changing public API payloads or execution.
- Group finalized selected Attention resources, visible context, pinned context, surface-open targets, and legacy Recall/`working_memory` records into compact role views.
- Make the future Vantage Working Memory model inspectable: Attention is the broad turn selection layer, Recall is the memory-grounding role over that selection, and Working Memory is all selected or in-scope context.

## Key Functions

- `build_attention_recall_role_projection()`: consumes only finalized request/response dictionaries and returns the trace payload.

## Notable Behavior

- Roles include `answer_context`, `recall_context`, `surface_to_open`, `protocol_guidance`, and `pinned_or_continuity_context`.
- Resource entries include ids, kind/type, title/label, roles, provenance, selected/visible/pinned flags, compact summary/excerpt fields, and a best-effort `sent_to_response_llm` marker.
- The projection compares selected Attention ids with legacy Recall ids so trace readers can see overlap and gaps while `ChatService.search_context()` remains unchanged.
- Excerpts are bounded and intended for provenance/debugging only; this module does not expose hidden model reasoning or full artifact bodies.
