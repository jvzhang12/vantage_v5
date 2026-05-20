# `src/vantage_v5/services/context_handoff.py`

Internal read model for Attention, Recall, and Working Memory context handoff.

## Purpose

- Build `AttentionRecallContextHandoff` from finalized request/response payloads and from pre-generation ChatService context without changing retrieval, routing, UI actions, or writes.
- Represent selected Attention resources, visible context, pinned/continuity context, legacy Recall/search output, protocol guidance, and surface-open targets in one compact backend object.
- Provide the source model for generation recall-context adaptation, trace-only `attention_recall_context_handoff`, and the compatibility `attention_recall_role_projection`.

## Key Classes / Functions

- `ContextHandoffResource`: compact bounded resource DTO with id, kind/type, title, roles, origins, flags, provenance, short summary/excerpt, and a best-effort `sent_to_response_llm` marker.
- `AttentionRecallContextHandoff`: grouped handoff with role references, compact resources, selected-vs-recall comparison ids, and trace/projection serializers.
- `GenerationContextAdapterResult`: handoff-derived generation memory plus bounded parity diagnostics.
- `build_attention_recall_context_handoff()`: constructs the handoff from selected attention resources, visible artifacts, `recall`/`working_memory`, pinned context, and explicit surface-open targets.
- `adapt_handoff_to_generation_memory()`: maps handoff `recall_context` roles back into the `CandidateMemory` shape expected by chat generation while sanitizing Memory Trace ids/bodies.
- `sanitize_selected_attention_resources_for_generation()`: copies selected non-Memory-Trace Attention resources unchanged while replacing selected Memory Trace resources with safe prior-turn aliases and compact categorical fields before model input serialization.

## Notable Behavior

- Roles are `answer_context`, `recall_context`, `surface_to_open`, `protocol_guidance`, and `pinned_or_continuity_context`.
- The handoff compares selected Attention resource ids with legacy Recall ids so traces can show overlap and gaps while `ChatService.search_context()` remains the retrieval/vetting source.
- Summaries/excerpts are bounded and full `content` / `body` fields are never copied into the handoff.
- Memory Trace resources are public-sanitized as categorical prior-turn traces so raw user/assistant turn text is not copied into title, label, summary, excerpt, provenance label, or public resource id fields.
- Prompt-derived Memory Trace storage ids are replaced with per-turn safe aliases such as `memory_trace:prior-turn-1` in the handoff, role projection, Working Memory view, selected-Attention generation context, and role references; actual storage ids are not renamed.
- Synthetic `surface_to_open` placeholders that were not observed in selected, visible, recalled, or pinned context keep `sent_to_response_llm` unknown instead of claiming they grounded generation.
- This module is context plumbing only; it is not semantic intent authority and it does not affect routing or writes.
