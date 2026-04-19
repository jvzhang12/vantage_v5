# `src/vantage_v5/storage/memory_trace.py`

This module introduces the first-class Memory Trace store. It is separate from the JSON debug trace files in `traces/` and uses the same Markdown-first storage pattern as concepts, memories, and artifacts.

## Purpose

- Persist one structured Memory Trace record for each normal chat turn.
- Keep recent-turn continuity searchable without collapsing it into durable memories or artifacts.
- Preserve the experiment-vs-durable split by allowing the server to point chat at either a durable `memory_trace/` directory or a session-local one.

## Core Data Flow

- `MemoryTraceStore` subclasses `MarkdownRecordStore` with `source="memory_trace"` and `type="memory_trace"`.
- `create_turn_trace()` builds a timestamped record id, derives a title/card from the current user and assistant messages, links the record to recalled and learned ids when available, and renders a structured Markdown body containing the turn’s user message, assistant response, working-memory items, response-mode summary, whiteboard context, recent chat, and learned items.
- `list_recent_traces()` sorts trace records by their timestamp-prefixed ids and returns only the most recent slice for retrieval.

## Key Classes / Functions

- `MemoryTraceStore`: storage facade for Memory Trace records.
- `create_turn_trace()`: writes one turn-level Memory Trace record.
- `list_traces()` / `list_recent_traces()`: enumerate all or only the newest trace records.
- `_render_turn_trace_body()`: turns turn metadata into searchable Markdown.

## Notable Edge Cases

- Memory Trace records are distinct from the JSON `traces/` debug files; both are written by chat, but they serve different product roles.
- The store uses timestamp-prefixed ids so lexicographic filename order doubles as recency order.
- Whiteboard content may be omitted by the caller when the workspace buffer is transient, which keeps Memory Trace aligned with the same redaction boundary used by JSON debug traces.
