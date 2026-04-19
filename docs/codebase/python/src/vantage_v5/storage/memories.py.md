# `src/vantage_v5/storage/memories.py`

This module is the memory-specific wrapper around `MarkdownRecordStore`. `MemoryRecord` is an alias of `MarkdownRecord`, and `MemoryStore` configures the shared implementation with `source="memory"`, `default_type="memory"`, and `trust="medium"`.

Memories are stored as standalone Markdown records with frontmatter and body text managed by the base store. The wrapper only provides memory-flavored method names: `list_memories()` and `create_memory()` both delegate directly to the shared implementation.

The key constraint is that memory persistence is identical to artifacts and concepts at the storage layer, but the semantic defaults differ. New memory records default to the `memory` type and are treated as medium-trust records, which affects how they are surfaced elsewhere in the application.
