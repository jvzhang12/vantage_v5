# `src/vantage_v5/storage/concepts.py`

This module is a thin specialization of the shared markdown record store for concept notes. `ConceptRecord` is just an alias of `MarkdownRecord`, and `ConceptStore` configures the shared store to read and write concept files with `source="concept"`, `default_type="concept"`, and `trust="high"`.

Concepts are persisted as Markdown files managed by `MarkdownRecordStore`, which means each concept gets its own frontmatter-backed file with IDs, links, lineage, status, and body content. The convenience methods here are mostly naming wrappers: `list_concepts()` delegates to generic listing, `create_concept()` delegates to generic creation, and `create_revision()` maps a concept base ID to the shared revision workflow.

`upsert_protocol()` is the one stronger specialization. It writes a stable `type: protocol` concept record for recurring work instructions such as email drafting preferences, preserving structured frontmatter for `protocol_kind`, `variables`, `applies_to`, modifiability, and optional built-in override metadata used by the Inspect protocol editor.

The important constraint is that concept revisions are still file-based records, not in-place edits. The store’s revision flow creates a new record ID derived from the base concept, keeps the original concept’s links in the new revision, and preserves concept trust as high for downstream ranking and retrieval.
