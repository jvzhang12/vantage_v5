# `src/vantage_v5/storage/memory_trace.py`

This module introduces the first-class Memory Trace store. It is separate from the JSON debug trace files in `traces/` and uses the same Markdown-first storage pattern as concepts, memories, and artifacts.

## Purpose

- Persist one structured Memory Trace record for each normal chat turn.
- Keep recent-turn continuity searchable without collapsing it into durable memories or artifacts.
- Preserve the experiment-vs-durable split by allowing the server to point chat at either a durable `memory_trace/` directory or a session-local one.
- Carry structured trace metadata in YAML frontmatter so retrieval can rank recent turns by scope and grounding signals before falling back to transcript body text.

## Core Data Flow

- `MemoryTraceStore` subclasses `MarkdownRecordStore` with `source="memory_trace"` and `type="memory_trace"`.
- `create_turn_trace()` builds a timestamped record id, derives a title/card from the current user and assistant messages, links the record to recalled and learned ids when available, stores structured trace metadata such as `turn_mode`, `trace_scope`, `workspace_id`, `workspace_scope`, `grounding_mode`, response-mode counts, recalled ids/sources, learned ids/sources, history count, any preserved selected-context id, and an internal optional referenced-record fact in frontmatter, and renders a structured Markdown body containing the turn’s user message, assistant response, working-memory items, response-mode summary, whiteboard context, recent chat, learned items, preserved context, and referenced record when applicable.
- `list_recent_traces()` sorts trace records by their timestamp-prefixed ids and returns only the most recent slice for retrieval.
- `parse_memory_trace_metadata()` normalizes the stable public trace metadata back into a payload shape for chat / Scenario Lab turn responses and future inspection surfaces. Internal continuity-only metadata can still live in frontmatter without automatically becoming part of the public turn payload.

## Key Classes / Functions

- `MemoryTraceStore`: storage facade for Memory Trace records.
- `create_turn_trace()`: writes one turn-level Memory Trace record.
- `list_traces()` / `list_recent_traces()`: enumerate all or only the newest trace records.
- `parse_memory_trace_metadata()`: recovers trace-scope metadata for turn payloads.
- `_render_turn_trace_body()`: turns turn metadata into searchable Markdown.

## Notable Edge Cases

- Memory Trace records are distinct from the JSON `traces/` debug files; both are written by chat, but they serve different product roles.
- The store uses timestamp-prefixed ids so lexicographic filename order doubles as recency order.
- Whiteboard content may be omitted by the caller when the workspace buffer is transient, which keeps Memory Trace aligned with the same redaction boundary used by JSON debug traces.
- Search can rank the frontmatter trace metadata separately from body text, which keeps Memory Trace more precise without turning it into a second Library or a raw transcript viewer.
- Preserved selected context is recorded explicitly in metadata rather than inferred from the whole trace body, which lets continuity-aware retrieval stay bounded and inspectable.
- The optional referenced-record fact is deliberately internal: the server can use it to build navigator continuity, but chat does not automatically expose every continuity-only frontmatter key back through `memory_trace_record`.
