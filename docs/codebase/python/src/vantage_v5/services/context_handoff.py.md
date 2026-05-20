# `src/vantage_v5/services/context_handoff.py`

Internal read model for Attention, Recall, and Working Memory context handoff.

## Purpose

- Build `AttentionRecallContextHandoff` from finalized request/response payloads without changing retrieval, generation, routing, UI actions, or writes.
- Represent selected Attention resources, visible context, pinned/continuity context, legacy Recall/search output, protocol guidance, and surface-open targets in one compact backend object.
- Provide the source model for trace-only `attention_recall_context_handoff` and the compatibility `attention_recall_role_projection`.

## Key Classes / Functions

- `ContextHandoffResource`: compact bounded resource DTO with id, kind/type, title, roles, origins, flags, provenance, short summary/excerpt, and a best-effort `sent_to_response_llm` marker.
- `AttentionRecallContextHandoff`: grouped handoff with role references, compact resources, selected-vs-recall comparison ids, and trace/projection serializers.
- `build_attention_recall_context_handoff()`: constructs the handoff from selected attention resources, visible artifacts, `recall`/`working_memory`, pinned context, and explicit surface-open targets.

## Notable Behavior

- Roles are `answer_context`, `recall_context`, `surface_to_open`, `protocol_guidance`, and `pinned_or_continuity_context`.
- The handoff compares selected Attention resource ids with legacy Recall ids so traces can show overlap and gaps while `ChatService.search_context()` remains unchanged.
- Summaries/excerpts are bounded and full `content` / `body` fields are never copied into the handoff.
- This module is observability/read-model plumbing only; it is not semantic intent authority and it does not affect prompts or writes.
