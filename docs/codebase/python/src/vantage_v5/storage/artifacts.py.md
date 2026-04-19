# `src/vantage_v5/storage/artifacts.py`

This module is the artifact-facing wrapper around `MarkdownRecordStore`. `ArtifactRecord` is an alias of the shared record type, and `ArtifactStore` configures the storage layer for artifact content with `source="artifact"`, `default_type="artifact"`, and `trust="medium"`.

Artifacts persist as individual Markdown files with frontmatter metadata handled by the shared store. This wrapper now adds a small Scenario Lab convenience layer on top of that generic contract: `preview_artifact_id()` lets callers reserve the stable slug a new artifact will use, `create_artifact()` accepts an optional explicit `record_id`, and `scenario_metadata` can be injected into the Markdown body as a `## Scenario Metadata` block before the record is written.

`parse_artifact_scenario_metadata()` and `ArtifactStore.parse_scenario_metadata()` normalize the durable comparison-specific fields that Scenario Lab writes today. They read the Markdown metadata block first and then fall back to older comparison body conventions such as `Base Workspace`, `Question`, `## Branches Compared`, and `comes_from` when needed.

The main constraint is still that artifacts follow the shared Markdown record contract. There is no new persistence layer here; the extra scenario state lives in Markdown and is recovered through parse helpers rather than hidden storage.
