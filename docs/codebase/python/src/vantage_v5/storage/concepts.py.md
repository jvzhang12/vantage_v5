# `src/vantage_v5/storage/concepts.py`

This module is a thin specialization of the shared markdown record store for concept notes. `ConceptRecord` is just an alias of `MarkdownRecord`, and `ConceptStore` configures the shared store to read and write concept files with `source="concept"`, `default_type="concept"`, and `trust="high"`.

Concepts are persisted as Markdown files managed by `MarkdownRecordStore`, which means each concept gets its own frontmatter-backed file with IDs, links, lineage, status, and body content. The convenience methods here are only naming wrappers: `list_concepts()` delegates to generic listing, `create_concept()` delegates to generic creation, and `create_revision()` maps a concept base ID to the shared revision workflow.

The important constraint is that concept revisions are still file-based records, not in-place edits. The store’s revision flow creates a new record ID derived from the base concept, keeps the original concept’s links in the new revision, and preserves concept trust as high for downstream ranking and retrieval.
