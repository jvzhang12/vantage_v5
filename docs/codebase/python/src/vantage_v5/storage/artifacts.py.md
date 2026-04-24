# `src/vantage_v5/storage/artifacts.py`

This module is the artifact-facing wrapper around `MarkdownRecordStore`. `ArtifactRecord` is an alias of the shared record type, and `ArtifactStore` configures the storage layer for artifact content with `source="artifact"`, `default_type="artifact"`, and `trust="medium"`.

Artifacts persist as individual Markdown files with frontmatter metadata handled by the shared store. This wrapper now adds a small Scenario Lab convenience layer on top of that generic contract: `preview_artifact_id()` lets callers reserve the stable slug a new artifact will use, `create_artifact()` accepts an optional explicit `record_id`, and `scenario_metadata` can be injected into the Markdown body as a `## Scenario Metadata` block before the record is written while the same structured metadata is also preserved in record frontmatter.

`parse_artifact_scenario_metadata()` and `ArtifactStore.parse_scenario_metadata()` normalize the durable comparison-specific fields that Scenario Lab writes today. They read the stored record metadata first, then the Markdown metadata block, and then fall back to older comparison body conventions such as `Base Workspace`, `Question`, `## Branches Compared`, and `comes_from` when needed. Comparison artifacts now also recover a stable `branch_index` from Markdown frontmatter or the rendered branch-index section so revisit flows can surface branch id, title, label, and summary directly from the artifact.

`parse_artifact_lifecycle_metadata()` is the smaller parallel helper for ordinary artifact presentation. It does not invent a richer artifact storage layer; it simply recovers the explicit `artifact_origin` / `artifact_lifecycle` metadata stamped by the executor or Scenario Lab and falls back conservatively for legacy artifacts so serializers can expose whiteboard snapshots, promoted artifacts, and comparison hubs without guessing from `comes_from`.

The main constraint is still that artifacts follow the shared Markdown record contract. There is no new persistence layer here; the extra scenario state lives in Markdown and is recovered through parse helpers rather than hidden storage.
