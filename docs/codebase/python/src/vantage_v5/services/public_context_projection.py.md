# `src/vantage_v5/services/public_context_projection.py`

Shared public-safe projection helpers for Memory Trace, Recall, and Working Memory context rows.

## Purpose

- Centralize the browser/trace-safe Memory Trace projection used by `/api/chat` payload assembly, Attention/Recall handoff views, Working Memory view turn ids, Navigator selection summaries, and vetting summaries.
- Detect Memory Trace-derived rows even when they arrive through concept-shaped or memory-shaped compatibility arrays with raw Source Turn bodies.
- Replace prompt-derived ids with bounded public aliases without changing storage ids, retrieval selection, generation behavior, TurnPlan authority, or writes.

## Key Functions

- `public_memory_trace_record()`: projects the current turn Memory Trace record into the `current-turn` public alias with compact metadata and no body/content.
- `public_memory_trace_list()` / `public_memory_trace_item()`: project Memory Trace-derived rows into `memory_trace:prior-turn-N` entries with generic title/card/summary and no raw prompt or assistant text.
- `sanitize_public_attention_state_payload()`: applies the shared projection to public Attention candidates, Navigator selection, and selected Attention resources before response attachment.
- `public_attention_selection()`, `public_vetting_payload()`, `public_safe_id_list()`, and `public_turn_id()`: sanitize prompt-derived ids, including kind-prefixed `concept:turn-*` forms.
- `is_memory_trace_derived()` and `is_prompt_derived_id()`: shared detection primitives for public payload and trace-safe context helpers.

## Notable Behavior

- Safe Memory Trace aliases are `current-turn` for the current trace record and `memory_trace:prior-turn-N` for prior-turn context rows.
- Rows containing Memory Trace source markers such as `## Source Turn`, `## User Message`, or `## Assistant Response` are treated as Memory Trace-derived even if their `source` or `type` says concept, memory, artifact, or note.
- Non-Memory-Trace rows are copied unchanged by list projection so existing useful candidate fields remain available.
